from .utils import estimate_tokens

# Anthropic requires >=1024 tokens for a block to be cacheable
_MIN_CACHE_TOKENS = 1024

# Models that support prompt caching
_SUPPORTED_MODELS = {
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
    "claude-opus-4-5",
    "claude-sonnet-4-5",
    "claude-haiku-4-5",
    "claude-3-7-sonnet-20250219",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229",
    "claude-3-haiku-20240307",
}


class PromptCacheManager:
    def is_model_supported(self, model: str) -> bool:
        return any(model.startswith(m) or m.startswith(model) for m in _SUPPORTED_MODELS)

    def is_prompt_long_enough(self, text: str) -> bool:
        return estimate_tokens(text) >= _MIN_CACHE_TOKENS

    def wrap_system_prompt(self, system: str, model: str) -> list[dict] | str:
        """Return system as a cache-control block if eligible, else plain string."""
        if not system:
            return system
        if self.is_model_supported(model) and self.is_prompt_long_enough(system):
            return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        return system
