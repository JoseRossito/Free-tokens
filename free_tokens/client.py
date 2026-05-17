from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal

import anthropic
from dotenv import load_dotenv

from .conversation import ConversationManager
from .prompt_cache import PromptCacheManager
from .response_cache import ResponseCache
from .usage import UsageRecord, UsageTracker
from .utils import hash_request

if TYPE_CHECKING:
    from .storage import UsageStorage

load_dotenv()

Strategy = Literal["trim", "summarize"]


class FreeTokensClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_context_tokens: int = 150_000,
        context_strategy: Strategy = "trim",
        response_cache_enabled: bool = True,
        prompt_cache_enabled: bool = True,
        system: str = "",
        cache_dir: str | None = None,
        cache_ttl: int = 3600,
        storage: "UsageStorage | None" = None,
        session_id: str = "default",
    ):
        self._api_key = api_key or os.environ["ANTHROPIC_API_KEY"]
        self._model = model
        self._system = system
        self._response_cache_enabled = response_cache_enabled
        self._prompt_cache_enabled = prompt_cache_enabled
        self._storage = storage
        self._session_id = session_id

        self._anthropic = anthropic.Anthropic(api_key=self._api_key)
        self._conversation = ConversationManager(
            max_context_tokens=max_context_tokens,
            strategy=context_strategy,
            anthropic_client=self._anthropic,
            model=model,
        )
        self._prompt_cache = PromptCacheManager()
        self._response_cache = ResponseCache(cache_dir=cache_dir, ttl=cache_ttl)
        self.tracker = UsageTracker()

    def chat(self, user_message: str, max_tokens: int = 1024, temperature: float = 1.0) -> str:
        self._conversation.add_user_message(user_message)
        messages = self._conversation.get_messages()

        system = (
            self._prompt_cache.wrap_system_prompt(self._system, self._model)
            if self._prompt_cache_enabled
            else self._system
        )

        cache_key = hash_request(self._model, system, messages, max_tokens, temperature)

        if self._response_cache_enabled:
            cached = self._response_cache.get(cache_key)
            if cached is not None:
                text = cached["text"]
                self._conversation.add_assistant_message(text)
                rec = UsageRecord(
                    source="response_cache",
                    input_tokens=cached.get("input_tokens", 0),
                    output_tokens=cached.get("output_tokens", 0),
                    prompt_preview=user_message[:120],
                    model=self._model,
                    session_id=self._session_id,
                )
                self.tracker.record(rec)
                if self._storage is not None:
                    self._storage.save(rec)
                return text

        kwargs: dict = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if temperature != 1.0:
            kwargs["temperature"] = temperature
        if system:
            kwargs["system"] = system

        response = self._anthropic.messages.create(**kwargs)
        text = response.content[0].text

        usage = response.usage
        rec = UsageRecord(
            source="api",
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            prompt_preview=user_message[:120],
            model=self._model,
            session_id=self._session_id,
        )
        self.tracker.record(rec)
        if self._storage is not None:
            self._storage.save(rec)

        if self._response_cache_enabled:
            self._response_cache.set(
                cache_key,
                {
                    "text": text,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                },
            )

        self._conversation.add_assistant_message(text)
        return text

    def send_single(self, prompt: str, system: str = "", max_tokens: int = 1024) -> str:
        sys_block = (
            self._prompt_cache.wrap_system_prompt(system or self._system, self._model)
            if self._prompt_cache_enabled
            else (system or self._system)
        )
        messages = [{"role": "user", "content": prompt}]
        cache_key = hash_request(self._model, sys_block, messages, max_tokens, temperature=1.0)

        if self._response_cache_enabled:
            cached = self._response_cache.get(cache_key)
            if cached is not None:
                rec = UsageRecord(
                    source="response_cache",
                    input_tokens=cached.get("input_tokens", 0),
                    output_tokens=cached.get("output_tokens", 0),
                    prompt_preview=prompt[:120],
                    model=self._model,
                    session_id=self._session_id,
                )
                self.tracker.record(rec)
                if self._storage is not None:
                    self._storage.save(rec)
                return cached["text"]

        kwargs: dict = {"model": self._model, "max_tokens": max_tokens, "messages": messages}
        if sys_block:
            kwargs["system"] = sys_block

        response = self._anthropic.messages.create(**kwargs)
        text = response.content[0].text
        usage = response.usage

        rec = UsageRecord(
            source="api",
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            prompt_preview=prompt[:120],
            model=self._model,
            session_id=self._session_id,
        )
        self.tracker.record(rec)
        if self._storage is not None:
            self._storage.save(rec)

        if self._response_cache_enabled:
            self._response_cache.set(
                cache_key,
                {
                    "text": text,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                },
            )

        return text

    def reset_conversation(self) -> None:
        self._conversation.clear()

    def get_usage_report(self) -> None:
        self.tracker.print_report()
