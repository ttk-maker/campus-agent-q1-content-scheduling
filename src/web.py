"""Loopback-only UI and asynchronous JSON API; no third-party runtime dependencies."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading
from urllib.parse import urlsplit
import uuid

from .agent import Agent
from .domain import validate_data, validate_request
from .models import HTTPModel, MockModel, ModelError
from .store import DraftStore

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
LIMIT = 256 * 1024


class APIError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class Application:
    def __init__(self, database, model_factory=None):
        self.store = DraftStore(database)
        self.model_factory = model_factory or (lambda mode: MockModel() if mode == "mock" else HTTPModel())
        self.token = secrets.token_urlsafe(32)
        self.jobs = {}
        self.lock = threading.RLock()
        self.active = None
        self.data = read_json(ROOT / "data/fixtures.json")
        self.current_data = deepcopy(self.data)

    def bootstrap(self):
        scenarios = {p.stem: read_json(p) for p in (ROOT / "data/requests").glob("*.json")}
        return {"csrf_token": self.token, "data": self.data, "scenarios": scenarios,
                "model_name": os.environ.get("MODEL_NAME", "未配置"),
                "active_job": self.active, "published": False}

    def validate_payload(self, payload):
        if not isinstance(payload, dict) or not {"request", "data", "mode"} <= set(payload):
            raise ValueError("请求必须包含 request、data、mode")
        if set(payload) - {"request", "data", "mode", "max_steps", "fail_save"}:
            raise ValueError("存在未知请求字段")
        validate_request(payload["request"])
        validate_data(payload["data"])
        if payload["mode"] not in ("mock", "real"):
            raise ValueError("请选择离线演练或真实模型")
        budget = payload.get("max_steps", 24)
        if type(budget) is not int or not 1 <= budget <= 100:
            raise ValueError("步骤上限必须是 1 到 100 的整数")
        if type(payload.get("fail_save", False)) is not bool:
            raise ValueError("故障演练必须为布尔值")
        return deepcopy(payload)

    def start(self, payload, confirmation=None):
        payload = self.validate_payload(payload)
        with self.lock:
            if self.active:
                raise APIError(409, "已有任务正在执行，请等待完成后重试")
            try:
                model = self.model_factory(payload["mode"])
            except ModelError:
                raise APIError(503, "真实模型未配置；请启动 Ollama 并检查服务端环境变量") from None
            if confirmation:
                previous = self.jobs.get(confirmation.get("job_id"))
                if not previous or previous["state"] != "done":
                    raise APIError(409, "原任务不存在或尚未完成，请重新审核")
                if payload["request"] != previous["payload"]["request"] or payload["mode"] != previous["payload"]["mode"]:
                    raise APIError(409, "确认请求必须使用原始任务资料")
                item = next((i for i in previous["result"]["items"]
                             if i["asset_id"] == confirmation.get("asset_id")), None)
                if not item or not item.get("confirmation_token"):
                    raise APIError(409, "该素材没有待确认的时间建议")
                if (confirmation.get("slot") != item["suggested_at"] or
                        confirmation.get("confirmation_token") != item["confirmation_token"]):
                    raise APIError(409, "确认内容与页面展示的草稿版本不一致")
                consent = self.store.confirm(previous["result"]["request_id"], item["asset_id"],
                                             item["suggested_at"], expected_fingerprint=item["confirmation_token"])
                if consent["status"] != "confirmed":
                    raise APIError(409, "草稿已变化，旧页面不能确认；请重新审核")
            job_id = uuid.uuid4().hex
            self.current_data = deepcopy(payload["data"])
            self.jobs[job_id] = {"job_id": job_id, "state": "running", "payload": payload,
                                 "created_at": datetime.now(timezone.utc).isoformat(),
                                 "result": None, "trace": [], "error": None}
            self.active = job_id
            # Bound in-memory history; active run and the latest results remain available.
            while len(self.jobs) > 100:
                self.jobs.pop(next(iter(self.jobs)))
            threading.Thread(target=self._execute, args=(job_id, model), daemon=True).start()
            return {"job_id": job_id, "state": "running"}

    def _execute(self, job_id, model):
        with self.lock:
            payload = self.jobs[job_id]["payload"]
        agent = None
        try:
            self.store.initialize_schedule(payload["data"]["occupied"])
            agent = Agent(model, self.store, payload["data"],
                          max_steps=payload.get("max_steps", 24), fail_save=payload.get("fail_save", False))
            result = agent.run(payload["request"])
            with self.lock:
                self.jobs[job_id].update(state="done", result=result, trace=agent.trace)
        except Exception as exc:
            # Boundary handler: never expose stack traces, headers, credentials or claim a save.
            with self.lock:
                self.jobs[job_id].update(state="error", error="执行失败：" + type(exc).__name__ +
                                        "。请检查模型服务或资料；草稿实际状态可在草稿列表核对。",
                                        trace=agent.trace if agent else [])
        finally:
            with self.lock:
                self.active = None

    def job(self, job_id):
        with self.lock:
            if job_id not in self.jobs:
                raise APIError(404, "未找到运行记录，服务可能已重启；已保存草稿仍保留")
            return deepcopy(self.jobs[job_id])

    def confirm(self, payload):
        if not isinstance(payload, dict) or set(payload) != {"job_id", "asset_id", "slot", "confirmation_token"}:
            raise ValueError("确认参数不完整或包含未知字段")
        with self.lock:
            previous = self.jobs.get(payload["job_id"])
            if not previous:
                raise APIError(404, "原运行记录不存在，请重新审核后确认")
            latest = deepcopy(previous["payload"])
            latest["data"] = deepcopy(self.current_data)
            return self.start(latest, confirmation=payload)


def make_server(app, port=8765):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def send_bytes(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; script-src 'self'; style-src 'self'; "
                             "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def json(self, status, data):
            self.send_bytes(status, json.dumps(data, ensure_ascii=False, allow_nan=False).encode(),
                            "application/json; charset=utf-8")

        def check_host(self):
            if self.headers.get("Host") not in (f"127.0.0.1:{self.server.server_port}",
                                                f"localhost:{self.server.server_port}"):
                raise APIError(403, "仅允许本机访问")

        def do_GET(self):
            try:
                self.check_host()
                path = urlsplit(self.path).path
                if path in ("/", "/index.html", "/app.js", "/style.css", "/manual.html"):
                    name = "index.html" if path == "/" else path[1:]
                    kind = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}[Path(name).suffix]
                    self.send_bytes(200, (WEB / name).read_bytes(), kind + "; charset=utf-8")
                elif path == "/favicon.ico":
                    self.send_bytes(204, b"", "image/x-icon")
                elif path == "/api/health":
                    self.json(200, {"status": "ok", "published": False})
                elif path == "/api/bootstrap":
                    self.json(200, app.bootstrap())
                elif path == "/api/drafts":
                    self.json(200, {"drafts": app.store.list_drafts(), "published": False})
                elif path.startswith("/api/jobs/"):
                    self.json(200, app.job(path.rsplit("/", 1)[-1]))
                else:
                    raise APIError(404, "页面不存在。请打开首页 http://127.0.0.1:" + str(self.server.server_port) + "/")
            except APIError as exc:
                self.json(exc.status, {"error": exc.message})
            except Exception:
                self.json(500, {"error": "读取失败，请检查本地服务日志或重启服务"})

        def do_POST(self):
            try:
                self.check_host()
                origin = self.headers.get("Origin")
                if origin and origin != "http://" + self.headers.get("Host", ""):
                    raise APIError(403, "跨站请求被拒绝")
                if self.headers.get("X-CSRF-Token") != app.token:
                    raise APIError(403, "页面会话已过期，请刷新后重试")
                if self.headers.get_content_type() != "application/json":
                    raise APIError(415, "请使用 JSON 请求")
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    raise APIError(400, "请求长度无效") from None
                if not 0 < length <= LIMIT:
                    raise APIError(413, "请求为空或超过 256 KB")
                self.connection.settimeout(10)
                def invalid_constant(value):
                    raise ValueError("JSON 不允许非有限数字")
                payload = json.loads(self.rfile.read(length).decode("utf-8"), parse_constant=invalid_constant)
                path = urlsplit(self.path).path
                if path == "/api/jobs":
                    self.json(202, app.start(payload))
                elif path == "/api/confirm":
                    self.json(202, app.confirm(payload))
                else:
                    raise APIError(404, "API 路径不存在")
            except APIError as exc:
                self.json(exc.status, {"error": exc.message})
            except (ValueError, TypeError, KeyError, UnicodeError):
                self.json(400, {"error": "输入格式不正确，请检查请求、素材、时间及规则"})
            except Exception:
                self.json(500, {"error": "服务暂时无法处理请求；未报告保存成功"})

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description="Local content scheduling workbench")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default="runtime/workbench.db")
    args = parser.parse_args()
    os.environ.setdefault("MODEL_BASE_URL", "http://localhost:11434/v1")
    os.environ.setdefault("MODEL_NAME", "qwen2.5:7b-instruct")
    app = Application(args.db)
    server = make_server(app, args.port)
    print(f"Open http://127.0.0.1:{server.server_port}/ (UI); Ollama /v1 is an API base, not a webpage.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
