"""Validated input and deterministic business rules. No model authority here."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def instant(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string with timezone")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone is required")
    return parsed.astimezone(timezone.utc)


def canonical(value):
    return instant(value).isoformat()


def validate_request(request):
    if not isinstance(request, dict) or set(request) != {"request_id", "items"}:
        raise ValueError("request requires exactly request_id and items")
    if not isinstance(request["request_id"], str) or not request["request_id"].strip():
        raise ValueError("request_id is required")
    items = request["items"]
    if not isinstance(items, list) or not 1 <= len(items) <= 50:
        raise ValueError("items must contain 1..50 assets")
    seen = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {"asset_id", "requested_at", "hard_time"}:
            raise ValueError("item requires asset_id, requested_at, hard_time")
        if not isinstance(item["asset_id"], str) or not item["asset_id"].strip():
            raise ValueError("asset_id is required")
        if item["asset_id"] in seen:
            raise ValueError("duplicate asset in one request")
        seen.add(item["asset_id"])
        instant(item["requested_at"])
        if not isinstance(item["hard_time"], bool):
            raise ValueError("hard_time must be boolean")
    return request


def input_hash(item):
    return digest({**item, "requested_at": canonical(item["requested_at"])})


def check_rules(asset, rules):
    missing = [key for key in rules["required_fields"] if asset.get(key) in (None, "", [])]
    if missing:
        return {"status": "insufficient", "missing": missing, "risks": []}
    risks = []
    if asset.get("copyright_status") != "cleared":
        risks.append({"rule": "copyright", "reason": "copyright is not cleared"})
    duration = asset.get("duration_minutes")
    if type(duration) is not int or not 1 <= duration <= 180:
        risks.append({"rule": "duration", "reason": "duration must be integer 1..180"})
    if not isinstance(asset.get("channel"), str) or not isinstance(asset.get("title"), str):
        risks.append({"rule": "metadata_type", "reason": "channel and title must be strings"})
    content = str(asset.get("title", "")) + " " + str(asset.get("text", ""))
    for term in rules["blocked_terms"]:
        if term.casefold() in content.casefold():
            risks.append({"rule": "blocked_term", "reason": "contains prohibited claim: " + term})
    return {"status": "blocked" if risks else "passed", "missing": [], "risks": risks}


def overlaps(start, minutes, other_start, other_minutes):
    a, b = instant(start), instant(other_start)
    return a < b + timedelta(minutes=other_minutes) and b < a + timedelta(minutes=minutes)
