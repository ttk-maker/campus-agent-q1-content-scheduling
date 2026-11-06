import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import URLError

from src.models import HTTPModel, ModelError


class ModelAdapterTests(unittest.TestCase):
    def env(self):
        return patch.dict(os.environ, {"MODEL_API_KEY": "test-placeholder",
                                       "MODEL_BASE_URL": "https://example.invalid/v1",
                                       "MODEL_NAME": "test-model"}, clear=True)

    def test_observations_are_sent_back_and_next_action_is_parsed(self):
        sent = {}
        class Opener:
            def open(self, request, timeout):
                sent["body"] = json.loads(request.data)
                sent["timeout"] = timeout
                response = {"choices": [{"message": {"content": json.dumps({
                    "tool": "query_slots", "arguments": {}, "reason": "Find another free slot."})}}]}
                return io.BytesIO(json.dumps(response).encode())
        with self.env(), patch("urllib.request.build_opener", return_value=Opener()):
            model = HTTPModel()
            result = model.decide({"request": {"asset_id": "M01"}, "history": [{
                "action": {"tool": "save_draft", "arguments": {"suggested_at": "2026-11-07T18:00:00+08:00"},
                           "reason": "Save."},
                "observation": {"status": "rejected", "error": "slot_conflict"}
            }]})
        self.assertEqual(result["tool"], "query_slots")
        self.assertIn("slot_conflict", sent["body"]["messages"][-1]["content"])
        self.assertEqual(sent["body"]["messages"][-2]["role"], "assistant")
        self.assertEqual(sent["timeout"], 45)

    def test_network_errors_do_not_echo_key_or_response(self):
        class Opener:
            def open(self, request, timeout):
                raise URLError("sensitive-test-placeholder")
        with self.env(), patch("urllib.request.build_opener", return_value=Opener()):
            with self.assertRaises(ModelError) as raised:
                HTTPModel().decide({"request": {}, "history": []})
        self.assertNotIn("sensitive", str(raised.exception))
        self.assertIn("model_request_failed", str(raised.exception))

    def test_insecure_remote_endpoint_is_rejected(self):
        with self.env():
            os.environ["MODEL_BASE_URL"] = "http://example.invalid/v1"
            with self.assertRaises(ModelError):
                HTTPModel()

    def test_missing_configuration_is_explicit(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ModelError):
                HTTPModel()

    def test_local_ollama_does_not_require_a_key(self):
        with patch.dict(os.environ, {"MODEL_BASE_URL": "http://localhost:11434/v1",
                                     "MODEL_NAME": "qwen2.5:7b-instruct"}, clear=True):
            model = HTTPModel()
        self.assertIsNone(model.key)

    def test_remote_without_key_is_rejected(self):
        with patch.dict(os.environ, {"MODEL_BASE_URL": "https://example.invalid/v1",
                                     "MODEL_NAME": "test-model"}, clear=True):
            with self.assertRaises(ModelError):
                HTTPModel()
