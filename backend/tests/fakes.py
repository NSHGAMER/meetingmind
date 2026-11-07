"""Test doubles. FakeMemory mimics the documented Hindsight semantics the app relies on (per-user banks, tags with
any_strict matching, document_id replacement). It is a TEST double only: real Hindsight is exercised by
scripts/hindsight_smoke_test.py when a server/API key is available."""
import json
import re

from app.errors import HindsightUnavailable
from app.services.hindsight_gateway import MemoryGateway, MemoryHit
from app.services.llm import LLMClient


class FakeMemory(MemoryGateway):
    def __init__(self):
        super().__init__("http://fake", None, "test")
        self.banks: dict[str, dict[str, dict]] = {}  # bank -> document_id -> doc
        self.down = False

    def ensure_bank(self, user_id):
        if self.down:
            raise HindsightUnavailable("Hindsight is unreachable (test)")
        return self.banks.setdefault(self.bank_id(user_id), {}) and self.bank_id(user_id) or self.bank_id(user_id)

    def retain(self, user_id, content, *, document_id, tags, context, timestamp=None, metadata=None):
        self.ensure_bank(user_id)
        self.banks.setdefault(self.bank_id(user_id), {})[document_id] = {
            "content": content, "tags": tags, "metadata": metadata or {}}

    def recall(self, user_id, query, *, tags=None, tags_match="any_strict", max_tokens=2048, budget="mid"):
        self.ensure_bank(user_id)
        hits = []
        for doc_id, d in self.banks.get(self.bank_id(user_id), {}).items():
            if tags and not set(tags) & set(d["tags"]):
                continue
            for line in d["content"].split("\n"):
                if line.startswith("- "):
                    hits.append(MemoryHit(text=line[2:], type="world", document_id=doc_id, tags=d["tags"],
                                          metadata=d["metadata"]))
        return hits


class FakeLLM(LLMClient):
    """Deterministic stand-in: derives output from the prompt text, so tests verify the data flow, not a model."""

    def __init__(self):
        super().__init__("http://fake", "k", "fake-model", "fake")
        self.calls: list[tuple[str, str]] = []
        self.raw_override: str | None = None

    def _complete(self, messages):
        if self.raw_override is not None:
            return self.raw_override
        system, user = messages[0]["content"], messages[1]["content"]
        self.calls.append((system, user))
        if "extract structured facts" in system:
            return json.dumps(self._extract(user))
        if "persistent memory" in system:
            return json.dumps(self._briefing_memory(user))
        return json.dumps(self._briefing_generic())

    def _extract(self, user):
        notes = user.split("NOTES:\n", 1)[1]
        low = notes.lower()
        ex = {"summary": notes.split("\n")[0], "participants": ["Robert"], "topics": [], "discussions": [],
              "decisions": [], "commitments": [], "concerns": [], "preferences": [], "unresolved": [],
              "follow_ups": [], "suggested_status_updates": []}
        if "5 lakh" in low:
            ex["discussions"].append({"text": "Project budget is Rs 5 lakh", "topic": "Budget"})
        if "60 days" in low or "60-day" in low:
            ex["discussions"].append({"text": "Delivery required within 60 days", "topic": "Delivery timeline"})
        if "monthly payments" in low:
            ex["preferences"].append({"text": "Prefers monthly payments", "person": "Robert"})
            ex["discussions"].append({"text": "Payment preference: monthly", "topic": "Payment"})
        if "promised to send the detailed requirements document" in low:
            ex["commitments"].append({"description": "send the detailed requirements document",
                                      "owner_name": "Robert", "due_date": "2026-10-25", "kind": "commitment"})
        if "revised project timeline by november 10" in low:
            ex["commitments"].append({"description": "send the revised project timeline", "owner_name": "Me",
                                      "due_date": "2026-11-10", "kind": "commitment"})
        if "might" in low:
            ex["commitments"].append({"description": "maybe share sample data", "owner_name": "Robert",
                                      "due_date": None, "kind": "suggestion"})
        if "too tight" in low:
            ex["concerns"].append({"text": "60-day delivery timeline is too tight", "raised_by": "Robert"})
            ex["discussions"].append({"text": "Timeline concerns", "topic": "Delivery timeline"})
        if "still not been received" in low:
            ex["unresolved"].append("Requirements document still pending")
        if "document is received" in low or "document arrived" in low:
            m = re.search(r'"id": (\d+), "owner": "Robert"', user)
            if m:
                ex["suggested_status_updates"].append(
                    {"commitment_id": int(m.group(1)), "suggested_status": "completed", "evidence": "arrived"})
        ex["topics"] = sorted({d["topic"] for d in ex["discussions"] if d["topic"]})
        return ex

    def _briefing_memory(self, user):
        mems = re.findall(r"\[(M\d+)\][^\n]*", user)
        coms = re.findall(r"\[(C\d+)\] ([^\n]*)", user)
        lines = {m: l for m, l in re.findall(r"\[(M\d+)\]([^\n]*)", user)}
        hist = [{"text": l.strip(), "sources": [m]} for m, l in lines.items() if "discussed" in l]
        concerns = [{"text": l.strip(), "sources": [m]} for m, l in lines.items() if "CONCERN" in l]
        tps = [{"text": f"Follow up: {t[:80]}", "reason": "open commitment", "sources": [c]} for c, t in coms]
        return {"previous_interactions_summary": f"{len(mems)} memories recalled", "historical_context": hist,
                "previous_concerns": concerns, "things_to_remember": [
                    {"text": "Invented claim with no citation", "sources": []}],
                "talking_points": tps, "strategy": ["Lead with the open commitments"]}

    def _briefing_generic(self):
        return {"previous_interactions_summary": "", "historical_context": [], "previous_concerns": [],
                "things_to_remember": [], "talking_points": [
                    {"text": "Clarify goals", "reason": "generic", "sources": []}], "strategy": ["Be prepared"]}
