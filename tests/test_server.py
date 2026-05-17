import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


def _make_app(token: str | None = "test-secret"):
    tmpdir = tempfile.mkdtemp()
    env = {}
    if token is not None:
        env["FREE_TOKENS_API_TOKEN"] = token
    with patch.dict(os.environ, env):
        from free_tokens.server import create_app
        return create_app(storage_path=f"{tmpdir}/usage.db")


def test_health_always_accessible():
    from fastapi.testclient import TestClient
    app = _make_app(token=None)
    r = TestClient(app).get("/health")
    assert r.status_code == 200


def test_chat_401_without_token():
    from fastapi.testclient import TestClient
    app = _make_app()
    with patch.dict(os.environ, {"FREE_TOKENS_API_TOKEN": "test-secret"}):
        r = TestClient(app).post("/chat", json={"message": "hi"})
    assert r.status_code == 401


def test_chat_401_wrong_token():
    from fastapi.testclient import TestClient
    app = _make_app()
    with patch.dict(os.environ, {"FREE_TOKENS_API_TOKEN": "test-secret"}):
        r = TestClient(app).post(
            "/chat",
            json={"message": "hi"},
            headers={"Authorization": "Bearer wrong-token"},
        )
    assert r.status_code == 401


def test_chat_503_no_env_var():
    from fastapi.testclient import TestClient
    app = _make_app(token=None)
    env_without_token = {k: v for k, v in os.environ.items() if k != "FREE_TOKENS_API_TOKEN"}
    with patch.dict(os.environ, env_without_token, clear=True):
        r = TestClient(app).post("/chat", json={"message": "hi"})
    assert r.status_code == 503


def test_chat_200_with_correct_token():
    from fastapi.testclient import TestClient

    mock_ft = MagicMock()
    mock_ft.chat.return_value = "Hola!"
    mock_ft.tracker.api_calls.return_value = 1
    mock_ft.tracker.cache_hits.return_value = 0

    app = _make_app()
    with patch("free_tokens.server.FreeTokensClient", return_value=mock_ft):
        with patch.dict(os.environ, {"FREE_TOKENS_API_TOKEN": "test-secret"}):
            r = TestClient(app).post(
                "/chat",
                json={"message": "hi", "session_id": "s1"},
                headers={"Authorization": "Bearer test-secret"},
            )

    assert r.status_code == 200
    assert r.json()["response"] == "Hola!"
