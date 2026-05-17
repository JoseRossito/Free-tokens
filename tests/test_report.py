import tempfile
from datetime import datetime, timedelta
from free_tokens.report import _get_prices, _FALLBACK_PRICES
from free_tokens.storage import UsageStorage


def _make_storage_with_record(model: str, input_tokens: int, output_tokens: int, source: str = "api"):
    tmpdir = tempfile.mkdtemp()
    storage = UsageStorage(db_path=f"{tmpdir}/usage.db")

    class FakeRecord:
        timestamp = datetime.now()
        prompt_preview = ""
        session_id = "test"

    fake = FakeRecord()
    fake.source = source
    fake.input_tokens = input_tokens
    fake.output_tokens = output_tokens
    fake.cache_creation_input_tokens = 0
    fake.cache_read_input_tokens = 0
    fake.model = model
    fake.session_id = "test"
    fake.prompt_preview = ""
    storage.save(fake)
    return storage


def test_get_prices_haiku():
    p = _get_prices("claude-haiku-4-5")
    assert p == (1.00, 5.00, 0.10)


def test_get_prices_sonnet():
    p = _get_prices("claude-sonnet-4-6")
    assert p == (3.00, 15.00, 0.30)


def test_get_prices_opus():
    p = _get_prices("claude-opus-4-7")
    assert p == (15.00, 75.00, 1.50)


def test_get_prices_fallback_unknown_model():
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        p = _get_prices("gpt-4-turbo")
        assert p == _FALLBACK_PRICES
        assert len(w) == 1
        assert "fallback" in str(w[0].message).lower()


def test_prices_differ_across_models():
    in_haiku, out_haiku, _ = _get_prices("claude-haiku-4-5")
    in_sonnet, out_sonnet, _ = _get_prices("claude-sonnet-4-6")
    in_opus, out_opus, _ = _get_prices("claude-opus-4-7")

    tokens = 1_000_000
    cost_haiku = (tokens * in_haiku + tokens * out_haiku)
    cost_sonnet = (tokens * in_sonnet + tokens * out_sonnet)
    cost_opus = (tokens * in_opus + tokens * out_opus)

    assert cost_haiku < cost_sonnet < cost_opus


def test_report_runs_without_error():
    from free_tokens.report import ReportGenerator
    storage = _make_storage_with_record("claude-sonnet-4-6", 100, 50)
    gen = ReportGenerator(storage)
    gen.print_report(days=1)  # should not raise
