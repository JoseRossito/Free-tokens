import hashlib
import json


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def hash_request(model: str, system: str | list, messages: list, max_tokens: int) -> str:
    payload = json.dumps(
        {"model": model, "system": system, "messages": messages, "max_tokens": max_tokens},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()
