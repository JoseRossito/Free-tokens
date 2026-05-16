from free_tokens.prompt_cache import PromptCacheManager


pm = PromptCacheManager()

SHORT_TEXT = "Short"
LONG_TEXT = "word " * 900  # ~1125 tokens estimated (4500 chars // 4)


def test_unsupported_model_returns_string():
    result = pm.wrap_system_prompt(LONG_TEXT, "gpt-4")
    assert isinstance(result, str)


def test_short_prompt_returns_string():
    result = pm.wrap_system_prompt(SHORT_TEXT, "claude-sonnet-4-6")
    assert isinstance(result, str)


def test_long_prompt_supported_model_returns_block():
    result = pm.wrap_system_prompt(LONG_TEXT, "claude-sonnet-4-6")
    assert isinstance(result, list)
    assert result[0]["cache_control"] == {"type": "ephemeral"}
    assert result[0]["text"] == LONG_TEXT


def test_empty_system_returns_empty():
    result = pm.wrap_system_prompt("", "claude-sonnet-4-6")
    assert result == ""


def test_is_prompt_long_enough():
    assert not pm.is_prompt_long_enough("hi")
    assert pm.is_prompt_long_enough("a" * 4200)  # >1024 tokens
