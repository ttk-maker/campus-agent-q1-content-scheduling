import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from src.models import MockModel, ModelError
from src.web import Application, make_server, ROOT


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Application(Path(self.temp.name) / "web.db")
        self.server = make_server(self.app, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def call(self, path, body=None, headers=None):
        request = Request(self.base + path, data=json.dumps(body).encode() if body is not None else None,
                          headers={"Content-Type": "application/json", "X-CSRF-Token": self.app.token,
                                   **(headers or {})})
        try:
            with urlopen(request, timeout=5) as response:
                raw = response.read()
                return response.status, json.loads(raw) if response.headers.get_content_type() == "application/json" else raw
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def payload(self, case="conflict"):
        return {"request": json.loads((ROOT / "data/requests" / (case+".json")).read_text(encoding="utf-8")),
                "data": self.app.data, "mode": "mock"}

    def wait(self, job_id):
        for _ in range(100):
            code, result = self.call("/api/jobs/" + job_id)
            if result["state"] != "running":
                return result
            time.sleep(.01)
        self.fail("job timed out")

    def test_home_static_assets_manual_and_api(self):
        for path in ("/", "/index.html", "/app.js", "/style.css", "/manual.html", "/api/health", "/api/bootstrap"):
            with self.subTest(path=path):
                self.assertEqual(self.call(path)[0], 200)

    def test_job_repeat_and_confirmation_through_http(self):
        _, first = self.call("/api/jobs", self.payload())
        result = self.wait(first["job_id"])
        item = result["result"]["items"][0]
        self.assertEqual(item["status"], "needs_confirmation")
        _, repeat = self.call("/api/jobs", self.payload())
        repeated = self.wait(repeat["job_id"])
        self.assertEqual(repeated["result"]["items"][0]["save_status"], "existing")
        code, confirm = self.call("/api/confirm", {"job_id":first["job_id"],"asset_id":"M01",
                                                  "slot":item["suggested_at"],
                                                  "confirmation_token":item["confirmation_token"]})
        self.assertEqual(code, 202)
        confirmed = self.wait(confirm["job_id"])["result"]["items"][0]
        self.assertEqual(confirmed["draft_status"], "ready")
        self.assertEqual(confirmed["draft_id"], item["draft_id"])
        self.assertEqual(len(self.call("/api/drafts")[1]["drafts"]), 1)

    def test_unknown_api_and_path_traversal_return_404(self):
        for path in ("/v1", "/src/store.py", "/../.env", "/api/jobs/not-found"):
            self.assertEqual(self.call(path)[0], 404)

    def test_cross_site_mutation_rejected(self):
        self.assertEqual(self.call("/api/jobs", self.payload(), {"Origin":"https://example.invalid"})[0],403)
        self.assertEqual(self.call("/api/jobs", self.payload(), {"X-CSRF-Token":"invalid"})[0],403)

    def test_invalid_input_is_400_without_draft(self):
        payload = self.payload()
        payload["request"]["items"][0]["requested_at"] = "no time"
        self.assertEqual(self.call("/api/jobs", payload)[0],400)
        self.assertEqual(self.app.store.count(),0)

    def test_simulated_save_failure_returns_actual_failure(self):
        payload=self.payload("normal")
        payload["fail_save"]=True
        _, response=self.call("/api/jobs",payload)
        result=self.wait(response["job_id"])["result"]["items"][0]
        self.assertEqual(result["save_status"],"failed")
        self.assertEqual(self.app.store.count(),0)

    def test_concurrent_ui_submission_is_explicitly_busy(self):
        release=threading.Event()
        class Slow(MockModel):
            def decide(self,context):
                release.wait(2)
                return super().decide(context)
        self.app.model_factory=lambda mode:Slow()
        _, first=self.call("/api/jobs",self.payload())
        try:
            self.assertEqual(self.call("/api/jobs",self.payload())[0],409)
        finally:
            release.set()
            self.wait(first["job_id"])

    def test_unavailable_model_is_503_not_mock_fallback(self):
        def fail(mode):
            raise ModelError("missing")
        self.app.model_factory=fail
        payload=self.payload()
        payload["mode"]="real"
        self.assertEqual(self.call("/api/jobs",payload)[0],503)
        self.assertEqual(self.app.store.count(),0)

    def test_server_restart_keeps_drafts(self):
        _, job=self.call("/api/jobs",self.payload())
        self.wait(job["job_id"])
        second=Application(Path(self.temp.name)/"web.db")
        self.assertEqual(second.store.count(),1)
        self.assertIsNone(second.active)

    def test_stale_browser_confirmation_is_409(self):
        _, response=self.call("/api/jobs",self.payload())
        job=self.wait(response["job_id"])
        item=job["result"]["items"][0]
        payload=self.payload()
        payload["data"]["assets"]["M01"]["title"]="new version"
        _, response=self.call("/api/jobs",payload)
        self.wait(response["job_id"])
        self.assertEqual(self.call("/api/confirm",{"job_id":job["job_id"],"asset_id":"M01",
                         "slot":item["suggested_at"],"confirmation_token":item["confirmation_token"]})[0],409)

    def test_confirmation_does_not_restore_old_schedule_snapshot(self):
        _, response = self.call("/api/jobs", self.payload())
        first = self.wait(response["job_id"])
        item = first["result"]["items"][0]
        newer = self.payload("missing")
        newer["data"]["occupied"].append({"id":"new-19", "channel":"brand-main",
                                          "start":"2026-11-07T19:00:00+08:00", "duration_minutes":60})
        _, response = self.call("/api/jobs", newer)
        self.wait(response["job_id"])
        code, response = self.call("/api/confirm", {"job_id":first["job_id"], "asset_id":"M01",
                                  "slot":item["suggested_at"], "confirmation_token":item["confirmation_token"]})
        self.assertEqual(code, 202)
        latest = self.wait(response["job_id"])["result"]["items"][0]
        self.assertEqual(latest["status"], "needs_confirmation")
        self.assertIsNone(latest["effective_at"])
        self.assertTrue(latest["suggested_at"].startswith("2026-11-07T12:00"))
