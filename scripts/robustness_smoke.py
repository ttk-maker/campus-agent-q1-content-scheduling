"""Tiered robustness smoke tests, with actual results and durations."""
import io
import json
from pathlib import Path
import sys
import time
import unittest
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class RecordedResult(unittest.TextTestResult):
    def startTest(self, test):
        self.started = time.perf_counter()
        super().startTest(test)

    def record(self, test, status):
        self.records.append({"test": test.id(), "status": status,
                             "seconds": round(time.perf_counter()-self.started, 4)})

    def addSuccess(self, test):
        self.record(test, "passed")
        super().addSuccess(test)

    def addFailure(self, test, err):
        self.record(test, "failed")
        super().addFailure(test, err)

    def addError(self, test, err):
        self.record(test, "error")
        super().addError(test, err)


def main():
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "python": sys.version.split()[0],
              "mode": "deterministic-tests-and-mock", "tiers": []}
    output = ROOT / "examples/robustness"
    output.mkdir(parents=True, exist_ok=True)
    for tier, names in [
        ("1-basic-and-existing-guards", ["tests.test_scheduling", "tests.test_model_adapter"]),
        ("2-edge", ["tests.test_robustness.EdgeTests"]),
        ("3-difficult", ["tests.test_robustness.DifficultTests"]),
        ("4-http-integration", ["tests.test_web"]),
    ]:
        log = io.StringIO()
        runner = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=RecordedResult)
        RecordedResult.records = []
        result = runner.run(unittest.defaultTestLoader.loadTestsFromNames(names))
        (output / (tier+".txt")).write_text(log.getvalue(), encoding="utf-8")
        report["tiers"].append({"tier":tier, "passed":result.wasSuccessful(),
                                "tests":result.testsRun, "results":result.records[:]})
        print(tier, result.testsRun, "PASS" if result.wasSuccessful() else "FAIL")
    report["passed"] = all(tier["passed"] for tier in report["tiers"])
    report["total_tests"] = sum(tier["tests"] for tier in report["tiers"])
    (output/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
