"""Generate actual CLI evidence, including repeated saves and explicit confirmation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import sqlite3
from contextlib import closing
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("mock", "real"), default="mock")
    parser.add_argument("--case", help="Rerun one named scenario and update its manifest entry.")
    args = parser.parse_args()
    directory = ROOT / "examples" / args.mode
    manifest_path = directory / "manifest.json"
    manifest = (json.loads(manifest_path.read_text(encoding="utf-8"))
                if args.case and manifest_path.exists() else
                {"mode": args.mode, "generated_at": datetime.now(timezone.utc).isoformat(),
                 "python": sys.version.split()[0], "cases": []})
    matched = False
    with tempfile.TemporaryDirectory() as temp:
        for name, source in [
            ("normal", "normal"), ("missing", "missing"), ("risk", "risk"),
            ("conflict", "conflict"), ("duplicate", "conflict"),
            ("save-failure", "save-failure"), ("supplement", "supplement"),
            ("changed-occupancy", "conflict"), ("confirmation", "conflict"),
            ("batch", "batch"), ("budget", "normal"),
        ]:
            if args.case and args.case != name:
                continue
            matched = True
            target = directory / name
            request = json.loads((ROOT / "data/requests" / (source + ".json")).read_text(encoding="utf-8"))
            fixture = json.loads((ROOT / "data/fixtures.json").read_text(encoding="utf-8"))
            write(target / "input.json", request)
            write(target / "fixture.json", fixture)
            db = str(Path(temp) / (name + ".db"))
            runs = 2 if name in ("duplicate", "confirmation", "changed-occupancy") else 1
            case = {"name": name, "generated_at": datetime.now(timezone.utc).isoformat(), "runs": []}
            for run in range(1, runs + 1):
                fixture_path = target / "fixture.json"
                if name == "changed-occupancy" and run == 2:
                    fixture["occupied"][0]["start"] = "2026-11-07T19:00:00+08:00"
                    fixture_path = target / "fixture-2.json"
                    write(fixture_path, fixture)
                if name == "confirmation" and run == 2:
                    previous = json.loads((target / "output-1.json").read_text(encoding="utf-8"))
                    slot = previous["items"][0]["suggested_at"]
                    confirm = [sys.executable, "-m", "src.cli", "confirm", "--db", db,
                               "--request-id", request["request_id"], "--asset-id", "M01", "--slot", slot]
                    consent = subprocess.run(confirm, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
                    (target / "user-confirmation.json").write_text(consent.stdout, encoding="utf-8")
                    if consent.returncode:
                        raise RuntimeError("confirmation failed; inspect generated evidence")
                trace = target / f"trace-{run}.jsonl"
                output = target / f"output-{run}.json"
                output.unlink(missing_ok=True)
                trace.unlink(missing_ok=True)
                cmd = [sys.executable, "-m", "src.cli", "run", "--mode", args.mode,
                       "--request", str(target / "input.json"), "--data", str(fixture_path),
                       "--db", db, "--trace", str(trace), "--output", str(output)]
                if name == "save-failure":
                    cmd.append("--simulate-save-failure")
                if name == "budget":
                    cmd.extend(["--max-steps", "2"])
                result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
                if not output.exists():
                    (target / f"startup-error-{run}.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
                    raise RuntimeError("run failed before producing evidence: " + name)
                actual = json.loads(output.read_text(encoding="utf-8"))
                portable = ["python"] + [p.replace(str(ROOT) + str(Path("/")), "") for p in cmd[1:]]
                portable = [("<temporary-db>" if p == db else p.replace(str(ROOT), ".").replace("\\", "/"))
                            for p in portable]
                case["runs"].append({"command_argv": portable, "exit_code": result.returncode,
                                     "statuses": [item["status"] for item in actual["items"]],
                                     "output": str(output.relative_to(ROOT)).replace("\\", "/"),
                                     "trace": str(trace.relative_to(ROOT)).replace("\\", "/")})
            with closing(sqlite3.connect(db)) as connection:
                rows = connection.execute("SELECT draft_id, status, requested_at, suggested_at FROM drafts").fetchall()
            write(target / "storage-summary.json", {"draft_count": len(rows), "drafts": rows})
            manifest["cases"] = [c for c in manifest["cases"] if c["name"] != name] + [case]
            print(name + ": " + ", ".join(case["runs"][-1]["statuses"]))
    if not matched:
        parser.error("unknown scenario")
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    write(directory / "manifest.json", manifest)


if __name__ == "__main__":
    main()
