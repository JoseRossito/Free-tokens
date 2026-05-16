from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from .utils import estimate_tokens

if TYPE_CHECKING:
    import anthropic

Strategy = Literal["trim", "summarize"]

_SUMMARIZE_PROMPT = (
    "Summarize the following conversation in 3-5 concise sentences, "
    "preserving the most important facts and decisions. "
    "Output only the summary, no preamble.\n\n"
)


class ConversationManager:
    def __init__(
        self,
        max_context_tokens: int = 150_000,
        strategy: Strategy = "trim",
        anthropic_client: "anthropic.Anthropic | None" = None,
        model: str = "claude-sonnet-4-6",
    ):
        self._max = max_context_tokens
        self._strategy = strategy
        self._client = anthropic_client
        self._model = model
        self._messages: list[dict] = []

    def add_user_message(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        self._messages.append({"role": "assistant", "content": content})

    def _estimated_tokens(self) -> int:
        return sum(estimate_tokens(m["content"]) for m in self._messages)

    def token_budget_remaining(self) -> int:
        return self._max - self._estimated_tokens()

    def get_messages(self) -> list[dict]:
        if self._estimated_tokens() > self._max * 0.8:
            if self._strategy == "trim":
                self._trim()
            else:
                self._summarize()
        return list(self._messages)

    def _trim(self) -> None:
        # Remove oldest pairs until we're under 80% budget
        while self._estimated_tokens() > self._max * 0.8 and len(self._messages) >= 2:
            # Remove oldest user+assistant pair
            self._messages = self._messages[2:]

    def _summarize(self) -> None:
        if not self._client or len(self._messages) < 4:
            self._trim()
            return

        # Keep the last 2 messages fresh; summarize everything before them
        to_summarize = self._messages[:-2]
        keep = self._messages[-2:]

        conversation_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in to_summarize
        )
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=512,
                messages=[{"role": "user", "content": _SUMMARIZE_PROMPT + conversation_text}],
            )
            summary = response.content[0].text
            self._messages = [
                {"role": "user", "content": f"[Earlier conversation summary: {summary}]"},
                {"role": "assistant", "content": "Understood, I have the context."},
                *keep,
            ]
        except Exception:
            self._trim()

    def clear(self) -> None:
        self._messages.clear()
