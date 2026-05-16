from free_tokens.usage import UsageRecord, UsageTracker


def test_tracker_empty():
    t = UsageTracker()
    assert t.total_input_tokens() == 0
    assert t.tokens_saved_response_cache() == 0
    assert t.api_calls() == 0


def test_tracker_api_record():
    t = UsageTracker()
    t.record(UsageRecord(source="api", input_tokens=100, output_tokens=50))
    assert t.total_input_tokens() == 100
    assert t.total_output_tokens() == 50
    assert t.api_calls() == 1
    assert t.cache_hits() == 0


def test_tracker_response_cache_hit():
    t = UsageTracker()
    t.record(UsageRecord(source="response_cache", input_tokens=200, output_tokens=80))
    assert t.tokens_saved_response_cache() == 280
    assert t.cache_hits() == 1
    assert t.api_calls() == 0


def test_tracker_prompt_cache():
    t = UsageTracker()
    t.record(UsageRecord(source="api", cache_read_input_tokens=1000))
    # 90% of 1000 = 900 saved
    assert t.tokens_saved_prompt_cache() == 900


def test_tracker_mixed():
    t = UsageTracker()
    t.record(UsageRecord(source="api", input_tokens=500, output_tokens=200))
    t.record(UsageRecord(source="response_cache", input_tokens=500, output_tokens=200))
    assert t.api_calls() == 1
    assert t.cache_hits() == 1
    assert t.tokens_saved_response_cache() == 700
