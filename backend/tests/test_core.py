import json

from .conftest import register


def test_auth_register_login_me_and_protection(env):
    c = env.client
    assert c.get("/api/meetings").status_code == 401
    h = register(c)
    assert c.get("/api/auth/me", headers=h).json()["email"] == "a@example.com"
    assert c.post("/api/auth/register", json={"email": "a@example.com", "name": "x", "password": "password123"}).status_code == 409
    assert c.post("/api/auth/login", json={"email": "a@example.com", "password": "wrongpass1"}).status_code == 401
    ok = c.post("/api/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    assert c.post("/api/auth/register", json={"email": "b@example.com", "name": "b", "password": "short"}).status_code == 422
    # password is hashed, not stored in clear
    from app.models import User
    with env.Session() as db:
        assert db.query(User).first().password_hash != "password123"


def test_contact_and_meeting_participants(env, auth):
    c = env.client
    r1 = c.post("/api/contacts", json={"full_name": "Robert", "organization": "ABC", "job_title": "Sales Manager"}, headers=auth)
    r2 = c.post("/api/contacts", json={"full_name": "Priya"}, headers=auth)
    assert r1.status_code == 201
    m = c.post("/api/meetings", headers=auth, json={
        "title": "Sync", "scheduled_at": "2026-12-01T10:00:00", "participant_ids": [r1.json()["id"], r2.json()["id"]]})
    assert m.status_code == 201 and {p["full_name"] for p in m.json()["participants"]} == {"Robert", "Priya"}
    upd = c.patch(f"/api/meetings/{m.json()['id']}", json={"participant_ids": [r1.json()["id"]], "title": "Sync 2"}, headers=auth)
    assert [p["full_name"] for p in upd.json()["participants"]] == ["Robert"] and upd.json()["title"] == "Sync 2"
    assert c.delete(f"/api/meetings/{m.json()['id']}", headers=auth).status_code == 204
    assert c.get(f"/api/meetings/{m.json()['id']}", headers=auth).status_code == 404


def _setup_demo(env, h):
    c = env.client
    assert c.post("/api/demo/load", headers=h).json()["loaded"]
    ms = sorted(c.get("/api/meetings", headers=h).json(), key=lambda m: m["scheduled_at"])
    return ms


def _analyze_confirm(c, h, mid):
    a = c.post(f"/api/meetings/{mid}/analyze", json={}, headers=h)
    assert a.status_code == 200, a.text
    ex = a.json()["extraction"]
    r = c.post(f"/api/meetings/{mid}/confirm", json={"extraction": ex}, headers=h)
    assert r.status_code == 200, r.text
    return ex


def test_analysis_does_not_write_until_confirmed(env, auth):
    c = env.client
    m1, m2, m3 = _setup_demo(env, auth)
    a = c.post(f"/api/meetings/{m1['id']}/analyze", json={}, headers=auth)
    ex = a.json()["extraction"]
    assert any("requirements document" in x["description"] for x in ex["commitments"])
    assert "Hindsight" in a.json()["processing_notice"]
    assert env.memory.banks == {} or not any(env.memory.banks.values())  # nothing retained yet
    assert c.get("/api/commitments", headers=auth).json() == []          # no records yet
    assert c.get(f"/api/meetings/{m1['id']}", headers=auth).json()["analysis_status"] == "pending_confirmation"


def test_full_three_meeting_demo_end_to_end(env, auth):
    c = env.client
    m1, m2, m3 = _setup_demo(env, auth)

    # Interaction 1: no history -> generic briefing, explicitly labelled
    g = c.post(f"/api/meetings/{m3['id']}/prepare", headers=auth).json()
    assert g["memory_used"] is False and g["memories_retrieved"] == 0
    assert g["draft"]["historical_context"] == [] and any("generic" in n for n in g["notes"])

    # Meeting 1 recorded -> confirm -> stored in Hindsight
    _analyze_confirm(c, auth, m1["id"])
    bank = env.memory.banks["test-user-1"]
    assert f"meeting-{m1['id']}" in bank
    assert "CONFIRMED COMMITMENT" in bank[f"meeting-{m1['id']}"]["content"]
    assert "5 lakh" in bank[f"meeting-{m1['id']}"]["content"]

    # Interaction 2: memory-powered briefing retrieves the pending commitment
    b1 = c.post(f"/api/meetings/{m3['id']}/prepare", headers=auth).json()
    assert b1["memory_used"] is True and b1["memories_retrieved"] > 0
    assert any("requirements document" in x["description"] for x in b1["pending_commitments"])
    assert not any("Invented" in i["text"] for i in b1["draft"]["things_to_remember"])  # uncited claim dropped
    for sec in ("historical_context",):
        for item in b1["draft"][sec]:
            assert item["sources"] and all(s in b1["references"] for s in item["sources"])
    assert any("uncited" in n for n in b1["notes"])

    # Meeting 2 -> evolving context: concern appears, document commitment still open (NOT auto-completed)
    _analyze_confirm(c, auth, m2["id"])
    b2 = c.post(f"/api/meetings/{m3['id']}/prepare", headers=auth).json()
    assert any("too tight" in i["text"] for i in b2["draft"]["previous_concerns"])
    doc = [x for x in b2["pending_commitments"] if "requirements document" in x["description"]][0]
    assert doc["status"] == "overdue"  # due Oct 25, still not completed
    assert len(b2["overview"]["previous_meetings"]) == 2
    assert b2["memories_retrieved"] > b1["memories_retrieved"]

    # Commitment tracker + memory overview reflect real operations
    cm = c.get("/api/commitments?filter=overdue", headers=auth).json()
    assert any("requirements document" in x["description"] for x in cm)
    ov = c.get("/api/memory/overview", headers=auth).json()
    assert ov["retain_operations"] == 2 and ov["recall_operations"] >= 2 and ov["facts_recalled_total"] > 0
    assert {t["topic"] for t in ov["frequent_topics"]} >= {"Budget", "Delivery timeline"}
    assert ov["contact_summaries"][0]["meetings"] == 2

    # Relationship intelligence is built from records, not hardcoded
    cid = c.get("/api/contacts", headers=auth).json()[0]["id"]
    p = c.get(f"/api/contacts/{cid}/profile", headers=auth).json()
    assert "2 recorded meetings" in p["relationship_summary"] and "Delivery timeline (3x)" in p["relationship_summary"]
    assert p["hindsight_memories"] and p["hindsight_error"] is None


def test_suggestion_is_not_a_commitment_and_status_never_auto_completes(env, auth):
    c = env.client
    m1, m2, m3 = _setup_demo(env, auth)
    c.patch(f"/api/meetings/{m2['id']}", json={"notes": "Robert might share sample data. Requirements document arrived? No: "
                                               "the requirements document has still not been received."}, headers=auth)
    _analyze_confirm(c, auth, m1["id"])
    ex = _analyze_confirm(c, auth, m2["id"])
    assert any(x["kind"] == "suggestion" for x in ex["commitments"])
    descs = [x["description"] for x in c.get("/api/commitments", headers=auth).json()]
    assert not any("sample data" in d for d in descs)  # suggestion never became a commitment
    doc = [x for x in c.get("/api/commitments", headers=auth).json() if "requirements" in x["description"]][0]
    assert doc["stored_status"] == "pending"


def test_status_update_requires_user_acceptance_and_supersedes_memory(env, auth):
    c = env.client
    m1, m2, m3 = _setup_demo(env, auth)
    _analyze_confirm(c, auth, m1["id"])
    cid = c.get("/api/commitments", headers=auth).json()[0]["id"]
    c.patch(f"/api/meetings/{m2['id']}", json={"notes": "Requirements document arrived today."}, headers=auth)
    a = c.post(f"/api/meetings/{m2['id']}/analyze", json={}, headers=auth).json()
    assert a["extraction"]["suggested_status_updates"][0]["commitment_id"] == cid
    # not accepted -> untouched
    c.post(f"/api/meetings/{m2['id']}/confirm", json={"extraction": a["extraction"]}, headers=auth)
    assert c.get("/api/commitments", headers=auth).json()[0]["stored_status"] == "pending"
    # accepted -> completed + superseding memory
    r = c.post(f"/api/meetings/{m2['id']}/confirm",
               json={"extraction": a["extraction"], "accepted_status_update_ids": [cid]}, headers=auth)
    assert r.json()["applied_status_updates"] == [cid]
    assert [x for x in c.get("/api/commitments", headers=auth).json() if x["id"] == cid][0]["status"] == "completed"
    assert "COMPLETED" in env.memory.banks["test-user-1"][f"commitment-{cid}"]["content"]


def test_manual_commitment_update_syncs_memory_and_reports_failure(env, auth):
    c = env.client
    m1, _, _ = _setup_demo(env, auth)
    _analyze_confirm(c, auth, m1["id"])
    cid = c.get("/api/commitments", headers=auth).json()[0]["id"]
    ok = c.patch(f"/api/commitments/{cid}", json={"status": "in_progress"}, headers=auth).json()
    assert ok["memory_synced"] is True
    env.memory.down = True
    bad = c.patch(f"/api/commitments/{cid}", json={"status": "completed"}, headers=auth).json()
    assert bad["memory_synced"] is False and "unreachable" in bad["memory_error"]
    assert bad["commitment"]["status"] == "completed"  # local change stands, failure is explicit


def test_hindsight_unavailable_is_a_clear_error_never_silent(env, auth):
    c = env.client
    m1, _, m3 = _setup_demo(env, auth)
    c.post(f"/api/meetings/{m1['id']}/analyze", json={}, headers=auth)
    env.memory.down = True
    ex = c.get(f"/api/meetings/{m1['id']}/analysis", headers=auth).json()["extraction"]
    r = c.post(f"/api/meetings/{m1['id']}/confirm", json={"extraction": ex}, headers=auth)
    assert r.status_code == 503 and r.json()["code"] == "hindsight_unavailable"
    m = c.get(f"/api/meetings/{m1['id']}", headers=auth).json()
    assert m["analysis_status"] == "pending_confirmation"           # nothing pretended
    assert c.get("/api/commitments", headers=auth).json() == []     # no records written
    assert c.get("/api/memory/health", headers=auth).status_code == 503
    # briefing in memory mode also fails loudly once history exists to recall; here participants exist -> recall fails
    assert c.post(f"/api/meetings/{m3['id']}/prepare", headers=auth).status_code == 503
    ov = c.get("/api/memory/overview", headers=auth).json()
    assert ov["failed_operations"] >= 1


def test_user_memory_and_data_isolation(env):
    c = env.client
    a, b = register(c, "a@example.com", "A"), register(c, "b@example.com", "B")
    m1, _, _ = _setup_demo(env, a)
    _analyze_confirm(c, a, m1["id"])
    assert set(env.memory.banks) == {"test-user-1"}
    # B cannot see or touch A's data
    assert c.get("/api/meetings", headers=b).json() == []
    assert c.get(f"/api/meetings/{m1['id']}", headers=b).status_code == 404
    assert c.post(f"/api/meetings/{m1['id']}/prepare", headers=b).status_code == 404
    assert c.get("/api/commitments", headers=b).json() == []
    cid = c.get("/api/contacts", headers=a).json()[0]["id"]
    assert c.get(f"/api/contacts/{cid}", headers=b).status_code == 404
    assert c.post("/api/meetings", headers=b, json={"title": "x", "scheduled_at": "2026-12-01T10:00:00",
                                                    "participant_ids": [cid]}).status_code == 404
    # B's own recall hits only B's (empty) bank
    mb = c.post("/api/meetings", headers=b, json={"title": "B meeting", "scheduled_at": "2026-12-01T10:00:00"}).json()
    br = c.post(f"/api/meetings/{mb['id']}/prepare", headers=b).json()
    assert br["memory_used"] is False and br["memories_retrieved"] == 0
    assert c.get("/api/memory/overview", headers=b).json()["retain_operations"] == 0


def test_invalid_llm_response_is_rejected_cleanly(env, auth):
    c = env.client
    m1, _, _ = _setup_demo(env, auth)
    env.llm.raw_override = "this is not json"
    r = c.post(f"/api/meetings/{m1['id']}/analyze", json={}, headers=auth)
    assert r.status_code == 502 and r.json()["code"] == "llm_invalid_response"
    env.llm.raw_override = json.dumps({"summary": 5, "commitments": "nope"})
    assert c.post(f"/api/meetings/{m1['id']}/analyze", json={}, headers=auth).status_code == 502
    assert c.get(f"/api/meetings/{m1['id']}", headers=auth).json()["analysis_status"] == "none"


def test_document_upload_restrictions(env, auth):
    c = env.client
    m1, _, _ = _setup_demo(env, auth)
    ok = c.post(f"/api/meetings/{m1['id']}/notes/upload", headers=auth, files={"file": ("n.txt", b"hello notes", "text/plain")})
    assert ok.status_code == 200 and ok.json()["notes"] == "hello notes"
    assert c.post(f"/api/meetings/{m1['id']}/notes/upload", headers=auth,
                  files={"file": ("evil.exe", b"MZ", "application/octet-stream")}).status_code == 415
    assert c.post(f"/api/meetings/{m1['id']}/notes/upload", headers=auth,
                  files={"file": ("big.txt", b"x" * (3 * 1024 * 1024), "text/plain")}).status_code == 413
