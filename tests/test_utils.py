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


def test_hash_request_different_temperature_produces_different_hash():
    msgs = [{"role": "user", "content": "same question"}]
    h1 = hash_request("model", "sys", msgs, 100, temperature=0.0)
    h2 = hash_request("model", "sys", msgs, 100, temperature=1.0)
    assert h1 != h2


def test_hash_request_different_top_p_produces_different_hash():
    msgs = [{"role": "user", "content": "same question"}]
    h1 = hash_request("model", "sys", msgs, 100, top_p=0.5)
    h2 = hash_request("model", "sys", msgs, 100, top_p=0.9)
    assert h1 != h2


def test_hash_request_same_temperature_deterministic():
    msgs = [{"role": "user", "content": "hi"}]
    h1 = hash_request("model", "sys", msgs, 100, temperature=0.7)
    h2 = hash_request("model", "sys", msgs, 100, temperature=0.7)
    assert h1 == h2
