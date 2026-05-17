from __future__ import annotations
import os
import uuid
from typing import Literal
try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from .client import FreeTokensClient
from .report import ReportGenerator
from .storage import UsageStorage


def create_app(
    model: str = "claude-sonnet-4-6",
    system: str = "You are a helpful assistant.",
    storage_path: str | None = None,
) -> "FastAPI":
    if not HAS_FASTAPI:
        raise ImportError("Install server dependencies: pip install 'free-tokens[server]'")

    app = FastAPI(title="Free Tokens API", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    storage = UsageStorage(storage_path)
    sessions: dict[str, FreeTokensClient] = {}

    def get_client(session_id: str) -> FreeTokensClient:
        if session_id not in sessions:
            sessions[session_id] = FreeTokensClient(model=model, system=system, storage=storage, session_id=session_id)
        return sessions[session_id]

    class ChatRequest(BaseModel):
        message: str
        session_id: str = "default"
        max_tokens: int = 1024

    class SingleRequest(BaseModel):
        prompt: str
        system: str = ""
        max_tokens: int = 1024

    class ChatResponse(BaseModel):
        response: str
        session_id: str
        api_calls: int
        cache_hits: int

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/chat", response_model=ChatResponse)
    def chat(req: ChatRequest):
        client = get_client(req.session_id)
        response = client.chat(req.message, max_tokens=req.max_tokens)
        return ChatResponse(
            response=response,
            session_id=req.session_id,
            api_calls=client.tracker.api_calls(),
            cache_hits=client.tracker.cache_hits(),
        )

    @app.post("/single")
    def single(req: SingleRequest):
        client = get_client("__single__")
        response = client.send_single(req.prompt, system=req.system, max_tokens=req.max_tokens)
        return {"response": response}

    @app.delete("/session/{session_id}")
    def reset_session(session_id: str):
        if session_id in sessions:
            sessions[session_id].reset_conversation()
        return {"reset": True}

    @app.get("/report")
    def report(days: int = 7):
        records = storage.get_records(__import__("datetime").datetime.now() - __import__("datetime").timedelta(days=days))
        return {"days": days, "total_records": len(records), "records": records}

    return app
