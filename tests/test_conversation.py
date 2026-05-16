from free_tokens.conversation import ConversationManager


def test_add_and_get_messages():
    cm = ConversationManager(max_context_tokens=10_000)
    cm.add_user_message("Hello")
    cm.add_assistant_message("Hi there")
    msgs = cm.get_messages()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"


def test_trim_removes_oldest_pairs():
    # max 200 tokens, each message ~25 tokens ("word " * 100 = 500 chars = 125 tokens)
    # we use short messages so trim kicks in when we have many
    cm = ConversationManager(max_context_tokens=50, strategy="trim")
    for i in range(10):
        cm.add_user_message("a" * 100)  # ~25 tokens each
        cm.add_assistant_message("b" * 100)
    msgs = cm.get_messages()
    # Should have trimmed down
    assert len(msgs) < 20


def test_budget_remaining_decreases():
    cm = ConversationManager(max_context_tokens=10_000)
    initial = cm.token_budget_remaining()
    cm.add_user_message("Hello world this is a test message.")
    assert cm.token_budget_remaining() < initial


def test_clear():
    cm = ConversationManager()
    cm.add_user_message("hi")
    cm.clear()
    assert cm.get_messages() == []


def test_summarize_fallback_to_trim_when_no_client():
    cm = ConversationManager(max_context_tokens=50, strategy="summarize")
    for i in range(10):
        cm.add_user_message("a" * 100)
        cm.add_assistant_message("b" * 100)
    msgs = cm.get_messages()
    # Falls back to trim since no anthropic client
    assert len(msgs) < 20
