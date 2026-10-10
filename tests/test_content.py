import json

REQ = {"topic": "Benefits of Generative AI", "content_type": "linkedin", "tone": "professional",
       "audience": "developers", "length": "short", "keywords": ["GenAI", "LLM"]}


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_requires_auth(client):
    assert client.post("/generate", json=REQ).status_code == 401


def test_login_and_me(client, auth):
    r = client.post("/auth/login", json={"email": "arjun@example.com", "password": "secret123"})
    assert r.status_code == 200
    assert client.get("/auth/me", headers=auth).json()["email"] == "arjun@example.com"
    assert client.post("/auth/login", json={"email": "arjun@example.com", "password": "wrong!!"}).status_code == 401


def test_generate_and_history(client, auth):
    r = client.post("/generate", json={**REQ, "versions": 2}, headers=auth)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    item = items[0]
    assert item["title"] == "Planned Title"
    assert item["hashtags"] == ["#GenAI", "#LLM"]
    assert item["review"]["overall"] == 9.0 and "seo_stats" in item["review"]
    assert item["cost_usd"] > 0
    hist = client.get("/content/history", headers=auth).json()
    assert len(hist) >= 2


def test_revision_loop_triggers_on_low_score(client, auth, fake_llm):
    fake_llm.review_overall = 4
    try:
        item = client.post("/generate", json=REQ, headers=auth).json()[0]
    finally:
        fake_llm.review_overall = 9
    assert any("revise" in t for t in item["trace"]) and any("revised draft" in t for t in item["trace"])


def test_rewrite_edit_approve_feedback_stats(client, auth):
    item = client.post("/generate", json=REQ, headers=auth).json()[0]
    rw = client.post("/rewrite", json={"content_id": item["id"], "instruction": "make it shorter"}, headers=auth)
    assert rw.status_code == 200 and rw.json()["parent_id"] == item["id"]
    up = client.patch(f"/content/{item['id']}", json={"generated_content": "Edited text", "status": "approved"}, headers=auth)
    assert up.json()["status"] == "approved" and up.json()["generated_content"] == "Edited text"
    assert client.post("/feedback", json={"content_id": item["id"], "rating": 5}, headers=auth).status_code == 201
    st = client.get("/stats", headers=auth).json()
    assert st["total_generations"] >= 3 and st["avg_rating"] == 5.0 and st["approved"] >= 1


def test_review_endpoint(client, auth):
    r = client.post("/review", json={"content": "This is some content that needs a review please."}, headers=auth)
    assert r.status_code == 200 and "scores" in r.json()


def test_documents_and_rag_generation(client, auth):
    up = client.post("/documents/upload", headers=auth,
                     files={"file": ("product.txt", b"Nimbus is our sync product. It syncs files instantly.", "text/plain")})
    assert up.status_code == 201 and up.json()["chunks"] >= 1
    assert client.post("/documents/upload", headers=auth, files={"file": ("x.exe", b"zz")}).status_code == 415
    item = client.post("/generate", json={**REQ, "topic": "Nimbus sync", "use_rag": True}, headers=auth).json()[0]
    assert item["sources"] == ["product.txt"]
    docs = client.get("/documents", headers=auth).json()
    assert client.delete(f"/documents/{docs[0]['id']}", headers=auth).status_code == 204


def test_stream(client, auth):
    with client.stream("POST", "/generate/stream", json=REQ, headers=auth) as r:
        events = [json.loads(l[6:]) for l in r.iter_lines() if l.startswith("data: ")]
    assert "".join(e["text"] for e in events if e["type"] == "token") == "Hello streamed world"
    assert events[-1]["type"] == "done" and events[-1]["content"]["generated_content"] == "Hello streamed world"


def test_isolation_between_users(client, auth):
    other = client.post("/auth/register", json={"email": "b@example.com", "password": "secret123"}).json()
    h2 = {"Authorization": f"Bearer {other['access_token']}"}
    mine = client.get("/content/history", headers=auth).json()[0]
    assert client.get(f"/content/{mine['id']}", headers=h2).status_code == 404
