"""Check recorded real or mock evidence against scenario acceptance criteria."""
import argparse
from datetime import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "normal": ["completed"], "missing": ["needs_information"], "risk": ["blocked"],
    "conflict": ["needs_confirmation"], "duplicate": ["needs_confirmation"],
    "save-failure": ["failed"], "supplement": ["completed"],
    "changed-occupancy": ["completed"], "confirmation": ["completed"],
    "batch": ["completed", "needs_confirmation", "needs_information"],
    "budget": ["budget_exhausted"],
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify(mode):
    root = ROOT / "examples" / mode
    manifest = load(root / "manifest.json")
    checks = []
    def check(label, value):
        checks.append({"check": label, "passed": bool(value)})
    for case in manifest["cases"]:
        name = case["name"]
        result = load(ROOT / case["runs"][-1]["output"])
        check(name + ": expected status", [i["status"] for i in result["items"]] == EXPECTED[name])
        check(name + ": mode labelled", result["mode"] == mode)
        check(name + ": never published", result["published"] is False and
              all(i["published"] is False for i in result["items"]))
        check(name + ": budget enforced", result["steps_used"] <= result["max_steps"])
        storage = load(root / name / "storage-summary.json")
        if name in ("missing", "risk", "save-failure", "budget"):
            check(name + ": no draft", storage["draft_count"] == 0)
        if name in ("duplicate", "confirmation", "changed-occupancy"):
            first = load(root / name / "output-1.json")["items"][0]
            second = result["items"][0]
            check(name + ": exactly one draft", storage["draft_count"] == 1)
            check(name + ": stable draft ID", first["draft_id"] == second["draft_id"])
            if name == "duplicate":
                check(name + ": existing result", second["save_status"] == "existing")
        if name == "conflict":
            item = result["items"][0]
            check(name + ": original requirement preserved", item["requested_at"] == "2026-11-07T18:00:00+08:00")
            check(name + ": suggests 19:00", datetime.fromisoformat(item["suggested_at"]) ==
                  datetime.fromisoformat("2026-11-07T19:00:00+08:00"))
            check(name + ": consent required", bool(item["pending_confirmations"]) and item["effective_at"] is None)
        if name == "confirmation":
            item = result["items"][0]
            check(name + ": confirmed ready", item["draft_status"] == "ready" and item["effective_at"] is not None)
        if name == "save-failure":
            check(name + ": honest save status", result["items"][0]["save_status"] == "failed")
    check("all scenarios present", set(c["name"] for c in manifest["cases"]) == set(EXPECTED))
    report = {"mode": mode, "passed": all(c["passed"] for c in checks),
              "checks_count": len(checks), "checks": checks}
    (root / "acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mode": mode, "passed": report["passed"], "checks": len(checks),
                      "failures": [c["check"] for c in checks if not c["passed"]]}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("mock", "real"), default="mock")
    raise SystemExit(verify(parser.parse_args().mode))
