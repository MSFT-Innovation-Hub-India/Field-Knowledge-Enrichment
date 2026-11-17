"""Model access (chat + embeddings) via Entra. Interfaces are small so tests can fake them."""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Protocol, TypeVar

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from pydantic import BaseModel, ValidationError

from ..settings import Settings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

_credential: DefaultAzureCredential | None = None


def get_credential() -> DefaultAzureCredential:
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential


class LlmClient(Protocol):
    def complete_json(self, system: str, user: str, model_cls: type[T]) -> T: ...
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class AzureLlmClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        provider = get_bearer_token_provider(get_credential(), settings.cognitive_scope)
        self._client = AzureOpenAI(
            azure_endpoint=settings.foundry_openai_endpoint,
            azure_ad_token_provider=provider,
            api_version="2025-04-01-preview",
            timeout=settings.model_timeout_s,
            max_retries=3,
        )

    def _chat(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self.settings.model_deployment,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            max_completion_tokens=6000,
        )
        return resp.choices[0].message.content or ""

    def complete_json(self, system: str, user: str, model_cls: type[T]) -> T:
        schema_hint = json.dumps(model_cls.model_json_schema(), ensure_ascii=False)
        sys_prompt = (
            f"{system}\n\nRespond with a single JSON object that conforms to this JSON schema "
            f"(no prose, no markdown fences):\n{schema_hint}"
        )
        last_error = ""
        for attempt in range(2):
            prompt = user if attempt == 0 else f"{user}\n\nYour previous reply was invalid ({last_error}). Return only valid JSON matching the schema."
            raw = self._chat(sys_prompt, prompt)
            try:
                return model_cls.model_validate_json(_strip_fences(raw))
            except (ValidationError, ValueError) as exc:
                last_error = str(exc)[:300]
                log.warning("Model output failed validation (attempt %d): %s", attempt + 1, last_error)
        raise ValueError(f"Model output invalid after retry: {last_error}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), 16):
            batch = texts[i:i + 16]
            for attempt in range(4):
                try:
                    resp = self._client.embeddings.create(model=self.settings.embedding_deployment, input=batch)
                    out.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
                    break
                except Exception:
                    if attempt == 3:
                        raise
                    time.sleep(2 ** attempt)
        return out


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw, re.DOTALL)
    return m.group(1) if m else raw
