"""Bounded model -> tool -> observation loop with independent business guards."""
from __future__ import annotations

from datetime import timedelta
import json
from pathlib import Path

from .domain import canonical, check_rules, instant, validate_request
from .models import ModelError


class Agent:
    def __init__(self, model, store, data, max_steps=24, fail_save=False, before_save=None):
        if type(max_steps) is not int or max_steps < 1:
            raise ValueError("max_steps must be a positive integer")
        self.model, self.store, self.data = model, store, data
        self.max_steps, self.fail_save, self.before_save = max_steps, fail_save, before_save
        self.trace = []

    def run(self, request):
        validate_request(request)
        self.trace = []
        results = []
        for item in request["items"]:
            results.append(self._run_item(request["request_id"], item))
        return {"request_id": request["request_id"], "mode": self.model.mode,
                "model": self.model.name, "max_steps": self.max_steps,
                "steps_used": len(self.trace), "published": False, "items": results}

    def _run_item(self, request_id, item):
        asset = review = saved = slots = None
        history = []
        terminal = None
        error = None
        while len(self.trace) < self.max_steps:
            context = {"request": {"request_id": request_id, **item}, "history": history}
            try:
                action = self.model.decide(context)
            except ModelError as exc:
                terminal, error = "failed", str(exc)
                self.trace.append({"step": len(self.trace) + 1, "asset_id": item["asset_id"],
                                   "action": {"tool": "model", "arguments": {}, "reason": "Request failed."},
                                   "observation": {"status": "failed", "error": error},
                                   "next_action": "stop"})
                break
            tool, args = (action.get("tool"), action.get("arguments")) if isinstance(action, dict) else (None, None)
            observation = {"status": "rejected", "error": "invalid_action"}
            valid = isinstance(action, dict) and set(action) == {"tool", "arguments", "reason"}
            valid = valid and isinstance(args, dict) and isinstance(action.get("reason"), str)
            if saved is not None and tool != "finish":
                observation = {"status": "rejected", "error": "draft_saved_finish_required"}
                valid = False
            if valid:
                try:
                    if tool == "read_asset" and set(args) == {"include_supplement"} and type(args["include_supplement"]) is bool:
                        asset = dict(self.data["assets"].get(item["asset_id"], {}))
                        if args["include_supplement"]:
                            asset.update(self.data.get("supplements", {}).get(item["asset_id"], {}))
                        review = slots = None
                        observation = {"status": "ok", "metadata": asset,
                                       "supplement_checked": args["include_supplement"]}
                    elif tool == "check_rules" and not args:
                        if asset is None:
                            observation = {"status": "rejected", "error": "read_required"}
                        else:
                            review = check_rules(asset, self.data["rules"])
                            observation = review
                    elif tool == "query_slots" and not args:
                        if not review or review["status"] != "passed":
                            observation = {"status": "rejected", "error": "review_required"}
                        else:
                            slots = []
                            for hours in range(4):
                                start = (instant(item["requested_at"]) + timedelta(hours=hours)).isoformat()
                                conflicts = self.store.conflicts(request_id, item["asset_id"], asset, start)
                                slots.append({"start": start, "available": not conflicts, "conflicts": conflicts})
                            observation = {"status": "ok", "slots": slots}
                    elif tool == "save_draft" and set(args) == {"suggested_at"}:
                        if not review or review["status"] != "passed" or check_rules(asset, self.data["rules"])["status"] != "passed":
                            observation = {"status": "rejected", "error": "review_required"}
                        elif not slots or canonical(args["suggested_at"]) not in {
                                s["start"] for s in slots if s["available"]}:
                            observation = {"status": "rejected", "error": "available_candidate_required"}
                        else:
                            if self.before_save:
                                self.before_save(self.store)
                            observation = self.store.save(request_id, item, asset, args["suggested_at"],
                                                          fail=self.fail_save)
                            if observation["status"] in ("saved", "existing"):
                                saved = observation
                    elif tool == "finish" and set(args) == {"outcome"}:
                        outcome = args["outcome"]
                        allowed = (
                            (outcome == "completed" and saved is not None) or
                            (outcome == "needs_information" and review and review["status"] == "insufficient") or
                            (outcome == "blocked" and review and review["status"] == "blocked") or
                            (outcome == "no_available_slot" and slots and not any(s["available"] for s in slots)) or
                            (outcome == "failed" and history and history[-1]["observation"]["status"] in ("failed", "rejected"))
                        )
                        if allowed:
                            terminal = outcome
                            observation = {"status": "finished", "outcome": outcome}
                        else:
                            observation = {"status": "rejected", "error": "unsupported_finish_claim"}
                except (ValueError, TypeError):
                    observation = {"status": "rejected", "error": "invalid_tool_arguments"}
            # Do not persist arbitrary model keys, internal analysis, or unbounded rationales.
            safe_action = {"tool": tool if isinstance(tool, str) else "invalid",
                           "arguments": args if isinstance(args, dict) else {},
                           "reason": str(action.get("reason", ""))[:240] if isinstance(action, dict) else ""}
            if history:
                history[-1]["next_action"] = safe_action["tool"]
            step = {"step": len(self.trace) + 1, "asset_id": item["asset_id"],
                    "action": safe_action, "observation": observation, "next_action": None}
            history.append(step)
            self.trace.append(step)
            if terminal:
                break
        terminal = terminal or "budget_exhausted"
        if history:
            history[-1]["next_action"] = "stop:" + terminal
        current = self.store.get(request_id, item["asset_id"]) if saved else None
        # Report persisted facts separately from whether the model completed its loop.
        pending = bool(current and current["status"] == "pending_confirmation")
        if terminal == "completed" and pending:
            terminal = "needs_confirmation"
        save_status = saved["status"] if saved else "not_attempted"
        attempts = [s["observation"] for s in history if s["action"]["tool"] == "save_draft"]
        if not saved and attempts:
            save_status = attempts[-1]["status"]
        return {
            "asset_id": item["asset_id"], "status": terminal,
            "review_status": review["status"] if review else "not_checked",
            "risk_reasons": review["risks"] if review else [],
            "missing_fields": review["missing"] if review else [],
            "requested_at": item["requested_at"], "hard_time": item["hard_time"],
            "suggested_at": current["suggested_at"] if current else None,
            "effective_at": current["suggested_at"] if current and current["status"] == "ready" else None,
            "pending_confirmations": ([{"type": "time_change", "original": item["requested_at"],
                                       "suggested": current["suggested_at"]}] if pending else []),
            "draft_id": current["draft_id"] if current else None,
            "draft_status": current["status"] if current else None,
            "save_status": save_status, "published": False,
            "error": error or (attempts[-1].get("error") if attempts else None)
        }

    def write_trace(self, path):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as stream:
            for step in self.trace:
                stream.write(json.dumps(step, ensure_ascii=False) + "\n")
