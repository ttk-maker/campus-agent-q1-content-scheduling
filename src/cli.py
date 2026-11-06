"""Run with python -m src.cli. Only trusted humans invoke confirm."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3

from .agent import Agent
from .models import HTTPModel, MockModel, ModelError
from .store import DraftStore
from .domain import validate_data, validate_request


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Review assets and save scheduling drafts; never publish.")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--request", required=True)
    run.add_argument("--data", default="data/fixtures.json")
    run.add_argument("--db", default="runtime/drafts.db")
    run.add_argument("--mode", choices=("mock", "real"), default="mock")
    run.add_argument("--max-steps", type=int, default=24, help="Total model action budget across all items.")
    run.add_argument("--trace", default="runtime/trace.jsonl")
    run.add_argument("--output", default="runtime/output.json")
    run.add_argument("--simulate-save-failure", action="store_true", help="Offline fault injection only.")
    confirm = sub.add_parser("confirm")
    confirm.add_argument("--db", default="runtime/drafts.db")
    confirm.add_argument("--request-id", required=True)
    confirm.add_argument("--asset-id", required=True)
    confirm.add_argument("--slot", required=True)
    args = parser.parse_args(argv)
    try:
        store = DraftStore(args.db)
        if args.command == "confirm":
            result = store.confirm(args.request_id, args.asset_id, args.slot)
        else:
            data = load(args.data)
            validate_data(data)
            request = validate_request(load(args.request))
            store.initialize_schedule(data["occupied"])
            model = MockModel() if args.mode == "mock" else HTTPModel()
            agent = Agent(model, store, data, max_steps=args.max_steps,
                          fail_save=args.simulate_save_failure)
            result = agent.run(request)
            agent.write_trace(args.trace)
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == "confirm":
            return 0 if result["status"] == "confirmed" else 2
        return 2 if any(i["status"] in ("failed", "budget_exhausted") for i in result["items"]) else 0
    except (ValueError, KeyError, OSError, sqlite3.Error, ModelError) as exc:
        # Avoid dumping data, HTTP responses or credentials in CLI errors.
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__,
                          "message": "Check input, storage and model configuration; see README."}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
