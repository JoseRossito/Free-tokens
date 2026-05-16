from free_tokens.utils import estimate_tokens, hash_request


def test_estimate_tokens_basic():
    assert estimate_tokens("hello") >= 1
    assert estimate_tokens("a" * 400) == 100


def test_estimate_tokens_minimum():
    assert estimate_tokens("") == 1


def test_hash_request_deterministic():
    h1 = hash_request("model", "sys", [{"role": "user", "content": "hi"}], 100)
    h2 = hash_request("model", "sys", [{"role": "user", "content": "hi"}], 100)
    assert h1 == h2


def test_hash_request_different_inputs():
    h1 = hash_request("model", "sys", [{"role": "user", "content": "hi"}], 100)
    h2 = hash_request("model", "sys", [{"role": "user", "content": "bye"}], 100)
    assert h1 != h2
