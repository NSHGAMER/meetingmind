"""Verifies a REAL Hindsight connection end to end (retain -> recall -> document replace) using the app's gateway.

Usage:
  From backend/:    python -m scripts.hindsight_smoke_test
  From project root: python backend/scripts/hindsight_smoke_test.py
Requires HINDSIGHT_API_URL (+ HINDSIGHT_API_KEY for Hindsight Cloud).
Retain is asynchronous inside Hindsight (fact extraction), so recall is polled for up to ~90 s.
"""
import os
import sys
import time
import uuid
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import get_settings
from app.errors import HindsightUnavailable
from app.services.hindsight_gateway import get_gateway

USER_ID = 999999  # dedicated throwaway bank: meetingmind-user-999999


def main() -> int:
    settings = get_settings()
    masked_key = f"{settings.hindsight_api_key[:6]}...{settings.hindsight_api_key[-4:]}" if settings.hindsight_api_key else "(none)"
    print(f"=== Hindsight Smoke Test ===")
    print(f"Configured Hindsight API URL: {settings.hindsight_api_url}")
    print(f"Configured Hindsight API Key: {masked_key}")
    print(f"Target Bank: {settings.hindsight_bank_prefix}-user-{USER_ID}")

    gw = get_gateway(reload=True)
    try:
        ping_result = gw.ping(USER_ID)
        print("Ping success:", ping_result)

        unique_id = uuid.uuid4().hex[:8]
        test_content = (
            f"- CONFIRMED COMMITMENT (status: pending), made in the October 20, 2026 meeting 'Smoke test {unique_id}': "
            f"Robert committed to send the requirements document {unique_id}; due October 25, 2026."
        )
        doc_id = f"meeting-smoke-{unique_id}"
        test_tag = f"smoke-{unique_id}"

        print(f"Retaining test fact (doc_id={doc_id})...")
        gw.retain(
            USER_ID,
            test_content,
            document_id=doc_id,
            tags=["user:999999", test_tag, "meeting:smoke"],
            context="smoke test",
            timestamp="2026-10-20T10:00:00Z",
            metadata={"meeting_id": f"smoke-{unique_id}"},
        )
        print("Fact retained. Polling recall...")

        for attempt in range(1, 19):
            hits = gw.recall(USER_ID, f"What did Robert promise to send {unique_id}?", tags=[test_tag])
            if hits:
                print(f"RECALL OK on attempt {attempt}: {len(hits)} fact(s) retrieved!")
                for h in hits:
                    print(f" - {h.text} | doc: {h.document_id}")
                gw.close()
                return 0
            time.sleep(5)

        print("Retained but nothing recalled within 90 s (extraction may still be running).")
        gw.close()
        return 2

    except HindsightUnavailable as e:
        print("HINDSIGHT ERROR:", e)
        gw.close()
        return 1
    except Exception as e:
        print("UNEXPECTED ERROR:", e)
        gw.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())
