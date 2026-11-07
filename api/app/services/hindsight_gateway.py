"""Thin wrapper over the official `hindsight-client` SDK.

Only documented SDK operations are used: create_bank, retain, recall, list_banks-free health probe via
recall on the user's bank. Every failure becomes HindsightUnavailable so callers can show a real error.
"""
import logging
from dataclasses import dataclass, field
from typing import Any

from ..config import get_settings
from ..errors import HindsightUnavailable

log = logging.getLogger("meetingmind.hindsight")

BANK_MISSION = (
    "Remember professional meeting history for one user: people and their roles and working preferences, "
    "what was discussed, decisions (approved/rejected/proposed), confirmed commitments with owner, deadline and "
    "status, concerns raised, unresolved issues and outcomes. Always keep the meeting date. Distinguish confirmed "
    "commitments from mere suggestions. A later update to a commitment supersedes earlier statements about it."
)


@dataclass
class MemoryHit:
    text: str
    type: str | None = None
    document_id: str | None = None
    context: str | None = None
    occurred: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryGateway:
    def __init__(self, base_url: str, api_key: str | None, bank_prefix: str):
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.api_key = api_key
        self.bank_prefix = bank_prefix
        self._client = None
        self._banks: set[str] = set()

    # -- helpers --
    def bank_id(self, user_id: int) -> str:
        return f"{self.bank_prefix}-user-{user_id}"  # one bank per user = hard isolation

    def _get(self):
        if self._client is None:
            try:
                from hindsight_client import Hindsight

                self._client = Hindsight(base_url=self.base_url, api_key=self.api_key, timeout=60.0)
            except Exception as e:  # pragma: no cover
                raise HindsightUnavailable(f"Could not initialise Hindsight client: {e}") from e
        return self._client

    def ensure_bank(self, user_id: int) -> str:
        bank = self.bank_id(user_id)
        if bank in self._banks:
            return bank
        try:
            self._get().create_bank(bank_id=bank, name=f"MeetingMind user {user_id}", mission=BANK_MISSION)
        except Exception as e:
            err_msg = str(e).lower()
            if "already exists" in err_msg or "409" in err_msg or "conflict" in err_msg:
                log.info("Hindsight bank %s already exists.", bank)
            else:
                raise HindsightUnavailable(f"Hindsight bank setup failed at {self.base_url}: {e}") from e
        self._banks.add(bank)
        return bank

    # -- operations --
    def retain(
        self,
        user_id: int,
        content: str,
        *,
        document_id: str,
        tags: list[str],
        context: str,
        timestamp: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> None:
        bank = self.ensure_bank(user_id)
        try:
            self._get().retain(
                bank_id=bank,
                content=content,
                context=context,
                timestamp=timestamp,
                document_id=document_id,  # re-retaining the same document_id replaces the old facts
                tags=tags,
                metadata=metadata,
            )
        except Exception as e:
            log.error("Hindsight retain failed: %s", e)
            raise HindsightUnavailable(f"Hindsight retain failed: {e}") from e

    def recall(
        self,
        user_id: int,
        query: str,
        *,
        tags: list[str] | None = None,
        tags_match: str = "any_strict",
        max_tokens: int = 2048,
        budget: str = "mid",
    ) -> list[MemoryHit]:
        bank = self.ensure_bank(user_id)
        try:
            resp = self._get().recall(
                bank_id=bank,
                query=query,
                types=["world", "experience"],
                max_tokens=max_tokens,
                budget=budget,
                tags=tags,
                tags_match=tags_match,
            )
        except Exception as e:
            log.error("Hindsight recall failed: %s", e)
            raise HindsightUnavailable(f"Hindsight recall failed: {e}") from e
        hits: list[MemoryHit] = []
        for r in resp.results or []:
            hits.append(
                MemoryHit(
                    text=r.text,
                    type=getattr(r, "type", None),
                    document_id=getattr(r, "document_id", None),
                    context=getattr(r, "context", None),
                    occurred=str(r.occurred_start) if getattr(r, "occurred_start", None) else None,
                    tags=list(getattr(r, "tags", None) or []),
                    metadata=dict(getattr(r, "metadata", None) or {}),
                )
            )
        return hits

    def ping(self, user_id: int) -> dict:
        """Real connectivity check: creates/validates the bank and runs a recall."""
        self.ensure_bank(user_id)
        self.recall(user_id, "connectivity check", max_tokens=64, budget="low", tags=None, tags_match="any")
        return {"ok": True, "url": self.base_url, "bank": self.bank_id(user_id)}

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None


_gateway: MemoryGateway | None = None


def get_gateway(*, reload: bool = False) -> MemoryGateway:
    global _gateway
    if reload and _gateway is not None:
        _gateway.close()
        _gateway = None
    if _gateway is None:
        s = get_settings()
        _gateway = MemoryGateway(s.hindsight_api_url, s.hindsight_api_key, s.hindsight_bank_prefix)
    return _gateway
