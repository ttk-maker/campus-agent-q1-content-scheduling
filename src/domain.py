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
    try:
        return parsed.astimezone(timezone.utc)
    except OverflowError:
        raise ValueError("timestamp outside supported range") from None


def canonical(value):
    return instant(value).isoformat()


def validate_request(request):
    if not isinstance(request, dict) or set(request) != {"request_id", "items"}:
        raise ValueError("request requires exactly request_id and items")
    if not isinstance(request["request_id"], str) or not 1 <= len(request["request_id"].strip()) <= 128:
        raise ValueError("request_id is required")
    items = request["items"]
    if not isinstance(items, list) or not 1 <= len(items) <= 50:
        raise ValueError("items must contain 1..50 assets")
    seen = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {"asset_id", "requested_at", "hard_time"}:
            raise ValueError("item requires asset_id, requested_at, hard_time")
        if not isinstance(item["asset_id"], str) or not 1 <= len(item["asset_id"].strip()) <= 128:
            raise ValueError("asset_id is required")
        if item["asset_id"] in seen:
            raise ValueError("duplicate asset in one request")
        seen.add(item["asset_id"])
        try:
            instant(item["requested_at"]) + timedelta(hours=6)
            datetime.fromisoformat(item["requested_at"].replace("Z", "+00:00")) + timedelta(hours=6)
        except OverflowError:
            raise ValueError("timestamp too close to calendar boundary") from None
        if not isinstance(item["hard_time"], bool):
            raise ValueError("hard_time must be boolean")
    return request


def input_hash(item):
    return digest({**item, "requested_at": canonical(item["requested_at"])})


def check_rules(asset, rules):
    required = set(rules["required_fields"]) | {"title", "channel", "duration_minutes", "copyright_status"}
    missing = [key for key in sorted(required) if asset.get(key) in (None, "", [])
               or isinstance(asset.get(key), str) and not asset[key].strip()]
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


def validate_data(data):
    if not isinstance(data, dict) or not {"assets", "rules", "occupied"} <= set(data):
        raise ValueError("资料必须包含 assets、rules 和 occupied")
    for key in ("assets", "supplements"):
        records = data.get(key, {})
        if not isinstance(records, dict) or len(records) > 200:
            raise ValueError("素材资料必须是至多 200 项的对象")
        for asset_id, asset in records.items():
            if not isinstance(asset_id, str) or not 1 <= len(asset_id.strip()) <= 128 or not isinstance(asset, dict):
                raise ValueError("素材 ID 或元数据格式错误")
            if len(json.dumps(asset, ensure_ascii=False)) > 12000:
                raise ValueError("单项素材资料超过 12000 字符")
    rules = data["rules"]
    if not isinstance(rules, dict):
        raise ValueError("rules 必须是对象")
    for name in ("required_fields", "blocked_terms"):
        values = rules.get(name)
        if not isinstance(values, list) or len(values) > 100 or any(
                not isinstance(v, str) or not 1 <= len(v.strip()) <= 200 for v in values):
            raise ValueError("规则字段必须为有限长度的非空字符串列表")
    entries = data["occupied"]
    if not isinstance(entries, list) or len(entries) > 500:
        raise ValueError("排期快照最多 500 项")
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict) or not {"id", "channel", "start", "duration_minutes"} <= set(entry):
            raise ValueError("排期字段不完整")
        for key in ("id", "channel"):
            if not isinstance(entry[key], str) or not 1 <= len(entry[key].strip()) <= 128:
                raise ValueError("排期 ID 或频道无效")
        if entry["id"] in seen:
            raise ValueError("排期 ID 重复")
        seen.add(entry["id"])
        if type(entry["duration_minutes"]) is not int or not 1 <= entry["duration_minutes"] <= 10080:
            raise ValueError("排期持续分钟须在 1 到 10080 之间")
        try:
            instant(entry["start"]) + timedelta(minutes=entry["duration_minutes"])
        except OverflowError:
            raise ValueError("排期超出日期范围") from None
    return data
