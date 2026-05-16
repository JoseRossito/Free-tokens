import tempfile
import pytest
from unittest.mock import MagicMock, patch


def _mock_response(text: str, input_tokens: int = 100, output_tokens: int = 50):
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.cache_creation_input_tokens = 0
    usage.cache_read_input_tokens = 0

    content = MagicMock()
    content.text = text

    response = MagicMock()
    response.content = [content]
    response.usage = usage
    return response


def _make_client(**kwargs):
    from free_tokens import FreeTokensClient

    tmpdir = tempfile.mkdtemp()
    return FreeTokensClient(
        api_key="sk-ant-test",
        cache_dir=tmpdir,
        **kwargs,
    )


def test_chat_calls_api_and_returns_text():
    client = _make_client()
    mock_resp = _mock_response("Hello!")

    with patch.object(client._anthropic.messages, "create", return_value=mock_resp):
        result = client.chat("Hi")

    assert result == "Hello!"
    assert client.tracker.api_calls() == 1


def test_response_cache_hit_skips_api():
    client = _make_client()
    mock_resp = _mock_response("Cached response")

    with patch.object(client._anthropic.messages, "create", return_value=mock_resp):
        client.chat("What is 2+2?")  # first call — miss, goes to API
        client.reset_conversation()
        result = client.chat("What is 2+2?")  # second call — should hit cache

    assert result == "Cached response"
    assert client.tracker.api_calls() == 1  # only 1 real API call
    assert client.tracker.cache_hits() == 1


def test_response_cache_disabled():
    client = _make_client(response_cache_enabled=False)
    mock_resp = _mock_response("Fresh")

    with patch.object(client._anthropic.messages, "create", return_value=mock_resp) as mock_create:
        client.send_single("ping")
        client.send_single("ping")

    assert mock_create.call_count == 2  # no caching → 2 real calls


def test_reset_conversation_clears_history():
    client = _make_client()
    mock_resp = _mock_response("ok")

    with patch.object(client._anthropic.messages, "create", return_value=mock_resp):
        client.chat("first message")
        client.reset_conversation()
        msgs = client._conversation.get_messages()

    assert msgs == []


def test_send_single_stateless():
    client = _make_client()
    mock_resp = _mock_response("answer")

    with patch.object(client._anthropic.messages, "create", return_value=mock_resp):
        r1 = client.send_single("question")
        r2 = client.send_single("question")

    assert r1 == r2 == "answer"
    # Second call hits response cache
    assert client.tracker.cache_hits() == 1


def test_usage_report_runs_without_error(capsys):
    client = _make_client()
    mock_resp = _mock_response("hi", input_tokens=200, output_tokens=100)

    with patch.object(client._anthropic.messages, "create", return_value=mock_resp):
        client.chat("test")

    client.get_usage_report()  # should not raise
