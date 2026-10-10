import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

from scene3d import HERO_3D
from styles import CSS

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
PLAN_LIMIT = int(os.getenv("PLAN_LIMIT", "100"))  # cosmetic usage meter only; not enforced by the API

TONES = ["professional", "friendly", "technical", "persuasive", "casual"]
AUDIENCES = ["beginners", "developers", "business", "general"]
TYPE_META = {
    "blog": ("📝", "Blog post"), "linkedin": ("💼", "LinkedIn"), "instagram": ("📸", "Instagram"),
    "email": ("✉️", "Email"), "twitter": ("🐦", "X / Twitter thread"),
}
REWRITES = ["Make it shorter", "Make it more professional", "Make it simpler", "Make it more engaging"]
PAGES = ["🏠  Dashboard", "✨  Create", "📚  Knowledge Base", "🗂  Library", "📊  Analytics"]

st.set_page_config(page_title="ContentAI · Create with agents", page_icon="✨", layout="wide")
st.markdown("<style>" + CSS + "</style>", unsafe_allow_html=True)

esc = html.escape


# ---------------- API helpers ----------------
def headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state.token}"}


def api(method: str, path: str, **kw):
    try:
        r = requests.request(method, f"{API_URL}{path}", headers=headers(), timeout=180, **kw)
    except requests.RequestException as e:
        st.error(f"Cannot reach the API at {API_URL}: {e}")
        return None
    if r.status_code == 401:
        st.session_state.token = None
        st.rerun()
    if not r.ok:
        is_json = r.headers.get("content-type", "").startswith("application/json")
        st.error(r.json().get("detail", r.text) if is_json else r.text)
        return None
    return r.json() if r.content else {}


# ---------------- small HTML helpers ----------------
def page_header(title: str, sub: str):
    st.markdown(f'<div class="eyebrow">ContentAI workspace</div><h1 class="page-title">{esc(title)}</h1>'
                f'<p class="page-sub">{esc(sub)}</p>', unsafe_allow_html=True)


def kpi(icon: str, label: str, value, sub: str = "", delay: float = 0) -> str:
    return (f'<div class="kpi tilt" style="animation-delay:{delay}s"><div class="kpi-ic">{icon}</div>'
            f'<div class="kpi-val">{esc(str(value))}</div><div class="kpi-lb">{esc(label)}</div>'
            f'<div class="kpi-sub">{esc(sub)}</div></div>')


def type_label(ctype: str) -> str:
    icon, name = TYPE_META.get(ctype, ("📄", ctype))
    return f"{icon} {name}"


def goto(page: str):
    st.session_state.page = page


# ---------------- auth / landing ----------------
def landing():
    left, right = st.columns([1.25, 1], gap="large")
    with left:
        st.markdown(
            '<div class="eyebrow">AI content platform</div>'
            '<div class="hero-title">Create content that <span class="grad-text">ships itself</span></div>'
            '<p class="hero-sub">An agentic pipeline plans, researches your documents, writes, reviews and optimises '
            'every post, blog, email and thread, in seconds.</p>',
            unsafe_allow_html=True,
        )
        if hasattr(st, "iframe"):  # newer Streamlit
            st.iframe(HERO_3D, height=400)
        else:
            components.html(HERO_3D, height=400)
        f1, f2, f3 = st.columns(3)
        for col, ic, t, d in (
            (f1, "🧠", "Agentic pipeline", "Plan, write, review, revise and SEO in one run."),
            (f2, "📚", "Your knowledge base", "RAG over your PDFs and docs with ChromaDB."),
            (f3, "⚡", "Groq speed", "Streaming drafts at lightning latency."),
        ):
            col.markdown(f'<div class="feature tilt"><div class="ic">{ic}</div><b>{t}</b><span>{d}</span></div>',
                         unsafe_allow_html=True)
    with right:
        st.markdown('<div style="height:2.2rem"></div>', unsafe_allow_html=True)
        st.markdown('<div class="brand"><div class="logo">✨</div>ContentAI</div>', unsafe_allow_html=True)
        tab_login, tab_reg = st.tabs(["Log in", "Create account"])
        for tab, path, label in ((tab_login, "/auth/login", "Log in"), (tab_reg, "/auth/register", "Get started free")):
            with tab:
                email = st.text_input("Work email", key=f"email{path}", placeholder="you@company.com")
                pw = st.text_input("Password", type="password", key=f"pw{path}", placeholder="At least 6 characters")
                if st.button(label, key=f"btn{path}", type="primary", use_container_width=True):
                    try:
                        r = requests.post(f"{API_URL}{path}", json={"email": email, "password": pw}, timeout=30)
                    except requests.RequestException as e:
                        st.error(f"Cannot reach the API at {API_URL}: {e}")
                        return
                    if r.ok:
                        st.session_state.token = r.json()["access_token"]
                        st.rerun()
                    else:
                        detail = r.json().get("detail", "Request failed")
                        st.error(detail if isinstance(detail, str) else "Check your email and password (min 6 characters).")
        st.caption("Secure JWT sign-in · Your documents stay private to your workspace")


# ---------------- result rendering ----------------
def score_bars(scores: dict) -> str:
    rows = ""
    for k, v in scores.items():
        rows += (f'<div class="bar-row"><div class="top"><span>{esc(k.replace("_", " ").title())}</span>'
                 f'<span>{v:.0f}/10</span></div><div class="bar"><i style="--w:{v * 10:.0f}%"></i></div></div>')
    return rows


def render_result(item: dict, key: str):
    rv = item.get("review") or {}
    overall = float(rv.get("overall") or 0)
    icon, name = TYPE_META.get(item["content_type"], ("📄", item["content_type"]))
    badge = '<span class="badge ok">APPROVED</span>' if item["status"] == "approved" else '<span class="badge draft">DRAFT</span>'

    left, right = st.columns([2, 1], gap="large")
    with left:
        st.markdown(f'<div class="eyebrow">{icon} {esc(name)} &nbsp; {badge}</div>'
                    f'<h2 style="margin:.2rem 0 .8rem">{esc(item["title"] or item["topic"])}</h2>', unsafe_allow_html=True)
        edited = st.text_area("Content (editable)", item["generated_content"], height=380, key=f"edit{key}",
                              label_visibility="collapsed")
        c1, c2, c3 = st.columns(3)
        if c1.button("💾 Save edits", key=f"save{key}", use_container_width=True):
            if api("PATCH", f"/content/{item['id']}", json={"generated_content": edited}) is not None:
                st.toast("Saved", icon="💾")
        if c2.button("✅ Approve", key=f"appr{key}", use_container_width=True, disabled=item["status"] == "approved"):
            if api("PATCH", f"/content/{item['id']}", json={"generated_content": edited, "status": "approved"}) is not None:
                st.toast("Approved and ready to publish", icon="✅")
                st.balloons()
        c3.download_button("⬇️ Download", edited, file_name=f"content_{item['id']}.md", key=f"dl{key}",
                           use_container_width=True)

        rc1, rc2 = st.columns([3, 1])
        instr = rc1.selectbox("Quick rewrite", REWRITES, key=f"rw{key}")
        rc2.markdown('<div style="height:1.75rem"></div>', unsafe_allow_html=True)
        if rc2.button("Rewrite", key=f"rwb{key}", use_container_width=True):
            with st.spinner("Rewriting..."):
                new = api("POST", "/rewrite", json={"content_id": item["id"], "instruction": instr})
            if new:
                st.session_state.results = [new]
                st.rerun()

        fb1, fb2, fb3 = st.columns([1.2, 3, 1.2])
        rating = fb1.slider("Rating", 1, 5, 4, key=f"rate{key}")
        comment = fb2.text_input("Feedback", key=f"cm{key}", placeholder="What could be better?")
        fb3.markdown('<div style="height:1.75rem"></div>', unsafe_allow_html=True)
        if fb3.button("Send", key=f"fb{key}", use_container_width=True):
            if api("POST", "/feedback", json={"content_id": item["id"], "rating": rating, "comment": comment}) is not None:
                st.toast("Thanks for the feedback!", icon="🙏")

    with right:
        st.markdown(
            f'<div class="glass"><div class="ring-wrap"><div class="ring" style="--v:{overall * 10:.0f}">'
            f'<div class="ring-in"><b>{overall:g}</b><small>/ 10</small></div></div>'
            f'<div class="ring-cap">Quality score</div></div>{score_bars(rv.get("scores", {}))}</div>',
            unsafe_allow_html=True,
        )
        tokens = item["input_tokens"] + item["output_tokens"]
        st.markdown(
            f'<div style="margin-top:.9rem"><span class="chip">🔤 {tokens:,} tokens</span>'
            f'<span class="chip cy">💲 {item["cost_usd"]:.5f}</span><span class="chip pk">⏱ {item["latency_s"]}s</span></div>',
            unsafe_allow_html=True,
        )
        if item["hashtags"] or item["seo_keywords"]:
            tags = "".join(f'<span class="chip">{esc(h)}</span>' for h in item["hashtags"])
            kws = "".join(f'<span class="chip cy">{esc(k)}</span>' for k in item["seo_keywords"])
            st.markdown(f'<div class="glass" style="margin-top:.6rem"><div class="eyebrow">Hashtags & SEO</div>'
                        f'<div style="margin-top:.5rem">{tags}{kws}</div>'
                        f'<div class="page-sub" style="margin:.4rem 0 0;font-size:.8rem">{esc(item["meta_description"])}</div></div>',
                        unsafe_allow_html=True)
        with st.expander("Review notes, SEO stats and agent trace"):
            for i in rv.get("issues", []):
                st.write(f"⚠️ {i}")
            for s in rv.get("suggestions", []):
                st.write(f"💡 {s}")
            if rv.get("seo_stats"):
                st.json(rv["seo_stats"])
            if item["sources"]:
                st.write("**Sources:**", ", ".join(item["sources"]))
            st.markdown('<ul class="timeline">' + "".join(f"<li>{esc(t)}</li>" for t in item["trace"]) + "</ul>",
                        unsafe_allow_html=True)


# ---------------- pages ----------------
def page_dashboard():
    me = api("GET", "/auth/me") or {}
    stats = api("GET", "/stats") or {}
    name = (me.get("email", "there").split("@")[0]).title()
    page_header(f"Welcome back, {name} 👋", "Here is what your content engine has been up to.")

    used = stats.get("total_generations", 0)
    cols = st.columns(4)
    cards = [("✨", "Generations", used, "all time"), ("✅", "Approved", stats.get("approved", 0), "ready to publish"),
             ("🔤", "Tokens used", f"{stats.get('input_tokens', 0) + stats.get('output_tokens', 0):,}", "input + output"),
             ("💲", "Estimated spend", f"${stats.get('total_cost_usd', 0)}", f"avg {stats.get('avg_latency_s', 0)}s per run")]
    for i, (col, c) in enumerate(zip(cols, cards)):
        col.markdown(kpi(*c, delay=i * 0.08), unsafe_allow_html=True)

    st.markdown('<div style="height:1.2rem"></div>', unsafe_allow_html=True)
    left, right = st.columns([2, 1], gap="large")
    with left:
        st.markdown('<div class="eyebrow">Quick start</div>', unsafe_allow_html=True)
        q1, q2, q3 = st.columns(3)
        for col, ic, t, d, pg in (
            (q1, "✨", "Create content", "Generate a post, blog or email.", PAGES[1]),
            (q2, "📚", "Add knowledge", "Upload docs to ground the AI.", PAGES[2]),
            (q3, "🗂", "Open library", "Edit, approve and download.", PAGES[3]),
        ):
            col.markdown(f'<div class="feature tilt"><div class="ic">{ic}</div><b>{t}</b><span>{d}</span></div>',
                         unsafe_allow_html=True)
            col.button("Open", key=f"qs{pg}", on_click=goto, args=(pg,), use_container_width=True)

        st.markdown('<div style="height:1rem"></div><div class="eyebrow">Recent content</div>', unsafe_allow_html=True)
        recent = api("GET", "/content/history", params={"limit": 5}) or []
        if not recent:
            st.markdown('<div class="glass" style="margin-top:.6rem">Nothing yet. Create your first piece of content ✨</div>',
                        unsafe_allow_html=True)
        for it in recent:
            q = (it.get("review") or {}).get("overall", "-")
            st.markdown(
                f'<div class="row"><div><div class="t">{esc(it["title"] or it["topic"])}</div>'
                f'<div class="m">{esc(type_label(it["content_type"]))} · {esc(it["created_at"][:16])}</div></div>'
                f'<div class="score-pill">{q}</div></div>', unsafe_allow_html=True)
    with right:
        pct = min(100, round(100 * used / PLAN_LIMIT)) if PLAN_LIMIT else 0
        st.markdown(
            f'<div class="glass tilt"><div class="eyebrow">Workspace usage</div>'
            f'<div class="kpi-val" style="margin-top:.4rem">{used}<span style="font-size:1rem;color:var(--muted)"> / {PLAN_LIMIT}</span></div>'
            f'<div class="meter"><i style="--w:{pct}%"></i></div>'
            f'<div class="kpi-lb">generations this workspace</div></div>', unsafe_allow_html=True)
        if stats.get("avg_rating"):
            st.markdown(f'<div class="glass" style="margin-top:.8rem"><div class="eyebrow">Your average rating</div>'
                        f'<div class="kpi-val">⭐ {stats["avg_rating"]}</div></div>', unsafe_allow_html=True)
        if stats.get("by_content_type"):
            st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)
            st.bar_chart(pd.Series({type_label(k): v for k, v in stats["by_content_type"].items()}), height=200)


def page_create():
    page_header("Create content", "Describe what you need. The agent plans, writes, reviews and optimises it.")
    with st.form("gen"):
        topic = st.text_input("What is it about?", placeholder="Benefits of Generative AI for small businesses")
        ctype = st.radio("Format", list(TYPE_META), format_func=type_label, horizontal=True)
        c1, c2, c3 = st.columns(3)
        tone = c1.selectbox("Tone", TONES)
        audience = c2.selectbox("Audience", AUDIENCES, index=1)
        length = c3.select_slider("Length", ["short", "medium", "long"], value="medium")
        k1, k2 = st.columns(2)
        keywords = k1.text_input("Keywords (comma separated)", placeholder="GenAI, LLM, RAG")
        extra = k2.text_input("Extra instructions (optional)", placeholder="Mention our free trial")
        o1, o2, o3 = st.columns(3)
        use_rag = o1.toggle("📚 Use my knowledge base")
        stream = o2.toggle("⚡ Stream live", value=True)
        versions = o3.slider("Versions", 1, 3, 1)
        go = st.form_submit_button("✨ Generate content", type="primary", use_container_width=True)

    if go:
        if len(topic.strip()) < 3:
            st.warning("Enter a topic first.")
            return
        body = {"topic": topic.strip(), "content_type": ctype, "tone": tone, "audience": audience, "length": length,
                "keywords": [k.strip() for k in keywords.split(",") if k.strip()], "use_rag": use_rag,
                "versions": versions, "extra_instructions": extra}
        if stream and versions == 1:
            status, box, text, final = st.empty(), st.empty(), "", None
            try:
                with requests.post(f"{API_URL}/generate/stream", json=body, headers=headers(), stream=True, timeout=180) as r:
                    if not r.ok:
                        st.error(r.text)
                        return
                    for line in r.iter_lines(decode_unicode=True):
                        if not line or not line.startswith("data: "):
                            continue
                        ev = json.loads(line[6:])
                        if ev["type"] == "status":
                            status.markdown(f'<div class="status-pill"><span class="pulse"></span>{esc(ev["text"])}</div>',
                                            unsafe_allow_html=True)
                        elif ev["type"] == "token":
                            text += ev["text"]
                            box.markdown(text + " ▍")
                        elif ev["type"] == "error":
                            st.error(ev["text"])
                            return
                        elif ev["type"] == "done":
                            final = ev["content"]
            except requests.RequestException as e:
                st.error(f"Streaming failed: {e}")
                return
            status.empty()
            box.empty()
            st.session_state.results = [final] if final else []
        else:
            with st.spinner("Agent is planning, writing and reviewing..."):
                st.session_state.results = api("POST", "/generate", json=body) or []

    results = st.session_state.get("results", [])
    if results:
        st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    if len(results) > 1:
        for i, tab in enumerate(st.tabs([f"Version {chr(65 + i)}" for i in range(len(results))])):
            with tab:
                render_result(results[i], f"v{results[i]['id']}")
    elif results:
        render_result(results[0], f"v{results[0]['id']}")


def page_knowledge():
    page_header("Knowledge base", "Upload reference material. Generation with the knowledge toggle on is grounded in it.")
    files = st.file_uploader("Drop PDF, DOCX, TXT, MD, CSV or JSON files", accept_multiple_files=True)
    if files and st.button("🚀 Index documents", type="primary"):
        for f in files:
            with st.spinner(f"Indexing {f.name}..."):
                r = api("POST", "/documents/upload", files={"file": (f.name, f.getvalue())})
            if r:
                st.toast(f"{r['filename']}: {r['chunks']} chunks indexed", icon="📚")
    docs = api("GET", "/documents") or []
    st.markdown(f'<div class="eyebrow" style="margin-top:1rem">Indexed documents · {len(docs)}</div>', unsafe_allow_html=True)
    if not docs:
        st.markdown('<div class="glass" style="margin-top:.6rem">No documents yet. Upload your product docs, brand guide or reports.</div>',
                    unsafe_allow_html=True)
    for d in docs:
        c1, c2 = st.columns([6, 1])
        c1.markdown(f'<div class="row"><div><div class="t">📄 {esc(d["filename"])}</div>'
                    f'<div class="m">{d["chunks"]} chunks · {esc(d["created_at"][:16])}</div></div></div>', unsafe_allow_html=True)
        if c2.button("Delete", key=f"del{d['id']}", use_container_width=True):
            api("DELETE", f"/documents/{d['id']}")
            st.rerun()


def page_library():
    page_header("Library", "Every piece you have generated. Search, edit, approve and download.")
    f1, f2 = st.columns([3, 1])
    query = f1.text_input("Search", placeholder="Search titles and topics", label_visibility="collapsed")
    only = f2.selectbox("Type", ["all", *TYPE_META], format_func=lambda x: "All types" if x == "all" else type_label(x),
                        label_visibility="collapsed")
    items = api("GET", "/content/history", params={"limit": 100}) or []
    items = [i for i in items if (only == "all" or i["content_type"] == only)
             and query.lower() in f'{i["title"]} {i["topic"]}'.lower()]
    if not items:
        st.markdown('<div class="glass">Nothing found.</div>', unsafe_allow_html=True)
    for it in items:
        icon = "✅" if it["status"] == "approved" else "📝"
        q = (it.get("review") or {}).get("overall", "-")
        with st.expander(f"{icon}  #{it['id']} · {it['title'] or it['topic']} · {type_label(it['content_type'])} · {it['created_at'][:16]} · ⭐ {q}"):
            edited = st.text_area("Content", it["generated_content"], height=260, key=f"lib{it['id']}", label_visibility="collapsed")
            a, b, c, d = st.columns(4)
            if a.button("💾 Save", key=f"ls{it['id']}", use_container_width=True):
                api("PATCH", f"/content/{it['id']}", json={"generated_content": edited})
                st.toast("Saved", icon="💾")
            if b.button("✅ Approve", key=f"la{it['id']}", use_container_width=True, disabled=it["status"] == "approved"):
                api("PATCH", f"/content/{it['id']}", json={"generated_content": edited, "status": "approved"})
                st.rerun()
            c.download_button("⬇️ Download", edited, file_name=f"content_{it['id']}.md", key=f"ld{it['id']}", use_container_width=True)
            if d.button("🗑 Delete", key=f"lx{it['id']}", use_container_width=True):
                api("DELETE", f"/content/{it['id']}")
                st.rerun()


def page_analytics():
    page_header("Analytics", "Usage, quality and cost across your workspace.")
    s = api("GET", "/stats")
    if not s:
        return
    cols = st.columns(5)
    data = [("✨", "Generations", s["total_generations"], ""), ("✅", "Approved", s["approved"], ""),
            ("🔤", "Tokens", f"{s['input_tokens'] + s['output_tokens']:,}", ""),
            ("💲", "Total cost", f"${s['total_cost_usd']}", ""), ("⭐", "Avg rating", s["avg_rating"] or "-", "")]
    for i, (col, c) in enumerate(zip(cols, data)):
        col.markdown(kpi(*c, delay=i * 0.07), unsafe_allow_html=True)
    st.markdown('<div style="height:1.2rem"></div>', unsafe_allow_html=True)
    l, r = st.columns(2, gap="large")
    with l:
        st.markdown('<div class="eyebrow">Content by format</div>', unsafe_allow_html=True)
        if s["by_content_type"]:
            st.bar_chart(pd.Series({type_label(k): v for k, v in s["by_content_type"].items()}))
        else:
            st.info("No data yet.")
    with r:
        st.markdown(f'<div class="glass tilt"><div class="eyebrow">Average latency</div>'
                    f'<div class="kpi-val">{s["avg_latency_s"]}s</div><div class="kpi-lb">per generation (all agent steps)</div></div>',
                    unsafe_allow_html=True)
        approved_pct = round(100 * s["approved"] / s["total_generations"]) if s["total_generations"] else 0
        st.markdown(f'<div class="glass" style="margin-top:.8rem"><div class="eyebrow">Approval rate</div>'
                    f'<div class="kpi-val">{approved_pct}%</div><div class="meter"><i style="--w:{approved_pct}%"></i></div></div>',
                    unsafe_allow_html=True)


# ---------------- main ----------------
if "token" not in st.session_state:
    st.session_state.token = None

if not st.session_state.token:
    landing()
else:
    with st.sidebar:
        st.markdown('<div class="brand"><div class="logo">✨</div>ContentAI</div>', unsafe_allow_html=True)
        page = st.radio("Navigation", PAGES, key="page", label_visibility="collapsed")
        st.markdown("---")
        st.caption(f"API · {API_URL}")
        if st.button("Log out", use_container_width=True):
            st.session_state.token = None
            st.session_state.pop("results", None)
            st.rerun()
    {PAGES[0]: page_dashboard, PAGES[1]: page_create, PAGES[2]: page_knowledge,
     PAGES[3]: page_library, PAGES[4]: page_analytics}[page]()
