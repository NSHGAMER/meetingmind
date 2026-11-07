"""Standalone full system verification for MeetingMind on Vercel."""
import os
import sys
import uuid
from pathlib import Path

# Add project root and backend to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
backend_dir = root_dir / "backend"
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from api.index import app
from app.database import init_db


def verify_all():
    print("=== MeetingMind Full-Stack System Verification ===")
    init_db()

    with TestClient(app) as client:
        # 1. Health checks
        print("1. Health checks...")
        r1 = client.get("/api/health")
        r2 = client.get("/health")
        assert r1.status_code == 200 and r2.status_code == 200
        print("   -> OK:", r1.json())

        # 2. Registration and login
        print("2. User registration and auth...")
        email = f"vercel_user_{uuid.uuid4().hex[:6]}@example.com"
        r_reg = client.post("/api/auth/register", json={"email": email, "password": "Password123!", "name": "Vercel User"})
        assert r_reg.status_code == 201
        token = r_reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("   -> Registered:", email)

        # 3. Contact creation
        print("3. Contact creation...")
        r_con = client.post(
            "/api/contacts",
            headers=headers,
            json={"full_name": "Sarah Connor", "job_title": "Director", "organization": "Cyberdyne"},
        )
        assert r_con.status_code == 201
        print("   -> Contact created:", r_con.json()["full_name"])

        # 4. Demo load
        print("4. Demo dataset loading (3 meetings, participants, notes)...")
        r_demo = client.post("/api/demo/load", headers=headers)
        assert r_demo.status_code == 200
        meeting_ids = r_demo.json()["meeting_ids"]
        print(f"   -> Loaded demo meeting IDs: {meeting_ids}")

        # 5. Dashboard
        print("5. Dashboard metrics...")
        r_dash = client.get("/api/dashboard", headers=headers)
        assert r_dash.status_code == 200
        dash = r_dash.json()
        print(f"   -> Total meetings: {dash['kpis']['total_meetings']}")

        # 6. Settings
        print("6. Settings & Diagnostics...")
        r_set = client.get("/api/settings/info", headers=headers)
        assert r_set.status_code == 200
        print(f"   -> Hindsight Cloud Bank: {r_set.json()['hindsight']['bank']}")

        # 7. Note analysis with Groq LLM and confirmation to Hindsight Cloud
        print("7. Analyzing Meeting 1 with Groq LLM...")
        m1_id = meeting_ids[0]
        r_ana = client.post(f"/api/meetings/{m1_id}/analyze", json={}, headers=headers)
        assert r_ana.status_code == 200
        extraction = r_ana.json()["extraction"]
        print(f"   -> Extracted {len(extraction['commitments'])} commitments, {len(extraction['discussions'])} discussions")

        print("   Retaining confirmed facts into Hindsight Cloud...")
        r_conf = client.post(f"/api/meetings/{m1_id}/confirm", json={"extraction": extraction}, headers=headers)
        assert r_conf.status_code == 200
        print("   -> Confirmed and retained successfully!")

        # 8. Commitments tracker
        print("8. Commitment tracking...")
        r_comm = client.get("/api/commitments", headers=headers)
        assert r_comm.status_code == 200
        comms = r_comm.json()
        assert len(comms) > 0
        cid = comms[0]["id"]
        r_patch = client.patch(f"/api/commitments/{cid}", headers=headers, json={"status": "in_progress"})
        assert r_patch.status_code == 200
        print(f"   -> Commitment #{cid} updated to in_progress")

        # 9. Briefing preparation with Hindsight recall + Groq
        print("9. Preparing Meeting 3 briefing with memory recall + Groq LLM...")
        target_meeting = meeting_ids[-1]
        r_prep = client.post(f"/api/meetings/{target_meeting}/prepare?mode=memory", headers=headers)
        assert r_prep.status_code == 200
        print("   -> Briefing generated with live memory recall!")

        # 10. Memory overview
        print("10. Memory intelligence audit overview...")
        r_mem = client.get("/api/memory/overview", headers=headers)
        assert r_mem.status_code == 200
        print(f"   -> Memory activity recorded: {r_mem.json()['meeting_interactions']} interactions")

        print("\n=======================================================")
        print("SUCCESS: ALL 10 PHASES VERIFIED END-TO-END!")
        print("=======================================================")


if __name__ == "__main__":
    verify_all()
