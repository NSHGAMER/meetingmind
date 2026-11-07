"""LLM interaction layer. Provider-agnostic (any OpenAI-compatible chat-completions endpoint, default Groq)."""
import json
import logging
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from ..config import get_settings
from ..errors import LLMError, LLMInvalidResponse

log = logging.getLogger("meetingmind.llm")
T = TypeVar("T", bound=BaseModel)


class LLMClient:
    def __init__(self, base_url: str, api_key: str | None, model: str, provider: str = "groq"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.provider = provider

    def describe(self) -> dict:
        return {"provider": self.provider, "model": self.model, "configured": bool(self.api_key)}

    def _complete(self, messages: list[dict]) -> str:
        if not self.api_key:
            raise LLMError("LLM_API_KEY is not configured on the server.")
        try:
            r = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
                timeout=90.0,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            err_body = e.response.text if hasattr(e, "response") else ""
            log.error("LLM call failed with status %s: %s", e.response.status_code, err_body)
            raise LLMError(f"LLM provider call failed ({e.response.status_code}): {err_body}") from e
        except (httpx.HTTPError, KeyError, ValueError) as e:
            log.error("LLM call failed: %s", e)
            raise LLMError(f"LLM provider call failed: {e}") from e

    def structured(self, system: str, user: str, schema: type[T]) -> T:
        """Call the model and validate against a Pydantic schema; one repair retry, then fail loudly."""
        messages = [
            {"role": "system", "content": system + "\nReturn ONLY a JSON object. No prose, no markdown fences."},
            {"role": "user", "content": user},
        ]
        last_err = ""
        for attempt in range(2):
            raw = self._complete(messages)
            try:
                return schema.model_validate_json(_strip_fences(raw))
            except (ValidationError, json.JSONDecodeError, ValueError) as e:
                last_err = str(e)[:600]
                log.warning("Invalid LLM output (attempt %d): %s", attempt + 1, last_err)
                messages += [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": f"That JSON failed validation: {last_err}\nReturn corrected JSON only."},
                ]
        raise LLMInvalidResponse(f"LLM returned invalid structured output: {last_err}")


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        s = s.rsplit("```", 1)[0]
    return s.strip()


_llm: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm
    if _llm is None:
        s = get_settings()
        _llm = LLMClient(s.llm_base_url, s.llm_api_key, s.llm_model, s.llm_provider)
    return _llm
