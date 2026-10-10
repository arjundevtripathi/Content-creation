"""Global CSS for the SaaS-style UI: animated mesh background, glass cards, 3D tilt, score ring."""

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

@property --v { syntax: '<number>'; inherits: false; initial-value: 0; }

:root{
  --bg:#070914; --card:rgba(255,255,255,.045); --card-hi:rgba(255,255,255,.08);
  --border:rgba(255,255,255,.10); --muted:#9aa3c7; --text:#e8eaf6;
  --p1:#7c5cff; --p2:#22d3ee; --p3:#f472b6; --ok:#34d399; --warn:#fbbf24;
}
html, body, .stApp, [class*="css"]{ font-family:'Inter',system-ui,sans-serif; }
.stApp{ background:var(--bg); color:var(--text); }

/* ---------- animated mesh background ---------- */
.stApp::before{
  content:""; position:fixed; inset:-25%; z-index:0; pointer-events:none; filter:blur(60px); opacity:.9;
  background:
    radial-gradient(40% 40% at 20% 25%, rgba(124,92,255,.35), transparent 70%),
    radial-gradient(35% 35% at 80% 20%, rgba(34,211,238,.25), transparent 70%),
    radial-gradient(40% 40% at 70% 85%, rgba(244,114,182,.22), transparent 70%);
  animation:drift 22s ease-in-out infinite alternate;
}
.stApp::after{
  content:""; position:fixed; inset:0; z-index:0; pointer-events:none; opacity:.35;
  background-image:linear-gradient(rgba(255,255,255,.04) 1px, transparent 1px),
                   linear-gradient(90deg, rgba(255,255,255,.04) 1px, transparent 1px);
  background-size:56px 56px;
  mask-image:radial-gradient(70% 60% at 50% 30%, #000 30%, transparent 100%);
  -webkit-mask-image:radial-gradient(70% 60% at 50% 30%, #000 30%, transparent 100%);
}
@keyframes drift{ 0%{transform:translate3d(-3%,-2%,0) scale(1)} 100%{transform:translate3d(4%,3%,0) scale(1.15)} }
[data-testid="stAppViewContainer"], [data-testid="stSidebar"]{ position:relative; z-index:1; }
header[data-testid="stHeader"]{ background:transparent; }
#MainMenu, footer, [data-testid="stToolbar"]{ visibility:hidden; }
.block-container{ padding-top:2rem; padding-bottom:4rem; max-width:1240px; animation:fadeUp .6s ease both; }
@keyframes fadeUp{ from{opacity:0; transform:translateY(14px)} to{opacity:1; transform:none} }

/* ---------- typography ---------- */
h1,h2,h3,h4{ font-family:'Space Grotesk','Inter',sans-serif; letter-spacing:-.02em; }
.grad-text{
  background:linear-gradient(100deg,#a78bfa,#22d3ee,#f472b6,#a78bfa); background-size:300% 100%;
  -webkit-background-clip:text; background-clip:text; color:transparent; animation:shine 8s linear infinite;
}
@keyframes shine{ to{background-position:300% 0} }
.hero-title{ font-family:'Space Grotesk',sans-serif; font-size:3.4rem; line-height:1.05; font-weight:700; margin:.2rem 0 1rem; }
.hero-sub{ color:var(--muted); font-size:1.08rem; line-height:1.6; max-width:34rem; }
.eyebrow{ text-transform:uppercase; letter-spacing:.14em; font-size:.72rem; color:var(--p2); font-weight:600; }
.page-title{ font-family:'Space Grotesk',sans-serif; font-size:2.1rem; font-weight:700; margin:0; }
.page-sub{ color:var(--muted); margin:.15rem 0 1.4rem; }

/* ---------- glass + 3D tilt ---------- */
.glass{
  background:var(--card); border:1px solid var(--border); border-radius:20px; padding:1.3rem 1.4rem;
  backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);
  box-shadow:0 10px 40px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.06);
}
.tilt{
  transform:perspective(900px) rotateX(0) rotateY(0) translateZ(0);
  transition:transform .35s cubic-bezier(.2,.8,.2,1), box-shadow .35s, border-color .35s;
  transform-style:preserve-3d; will-change:transform;
}
.tilt:hover{
  transform:perspective(900px) rotateX(5deg) rotateY(-6deg) translateY(-8px) translateZ(14px);
  border-color:rgba(124,92,255,.55); box-shadow:0 26px 60px rgba(124,92,255,.28), 0 0 0 1px rgba(124,92,255,.25);
}
.float{ animation:float 6s ease-in-out infinite; }
@keyframes float{ 0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)} }

/* KPI cards */
.kpi{ background:var(--card); border:1px solid var(--border); border-radius:20px; padding:1.1rem 1.2rem;
  backdrop-filter:blur(14px); position:relative; overflow:hidden; animation:fadeUp .6s ease both; }
.kpi::after{ content:""; position:absolute; inset:0; background:linear-gradient(120deg,transparent 30%,rgba(255,255,255,.07),transparent 70%);
  transform:translateX(-120%); animation:sweep 5s ease-in-out infinite; }
@keyframes sweep{ 0%,60%{transform:translateX(-120%)} 100%{transform:translateX(120%)} }
.kpi-ic{ font-size:1.5rem; margin-bottom:.35rem; }
.kpi-val{ font-family:'Space Grotesk',sans-serif; font-size:2rem; font-weight:700; line-height:1.1; }
.kpi-lb{ color:var(--muted); font-size:.82rem; margin-top:.15rem; }
.kpi-sub{ color:var(--ok); font-size:.75rem; margin-top:.25rem; min-height:1em; }

/* feature cards */
.feature{ background:var(--card); border:1px solid var(--border); border-radius:18px; padding:1rem 1.1rem; height:100%; }
.feature .ic{ font-size:1.6rem; }
.feature b{ display:block; margin:.35rem 0 .15rem; font-family:'Space Grotesk',sans-serif; }
.feature span{ color:var(--muted); font-size:.85rem; line-height:1.45; }

/* chips, badges, pills */
.chip{ display:inline-block; padding:.28rem .7rem; margin:0 .35rem .4rem 0; border-radius:999px; font-size:.78rem;
  background:rgba(124,92,255,.14); border:1px solid rgba(124,92,255,.35); color:#c9bfff; }
.chip.cy{ background:rgba(34,211,238,.10); border-color:rgba(34,211,238,.35); color:#8eeaf8; }
.chip.pk{ background:rgba(244,114,182,.10); border-color:rgba(244,114,182,.35); color:#fbb6da; }
.badge{ display:inline-block; padding:.18rem .6rem; border-radius:8px; font-size:.7rem; font-weight:600; letter-spacing:.04em; }
.badge.ok{ background:rgba(52,211,153,.15); color:var(--ok); } .badge.draft{ background:rgba(251,191,36,.14); color:var(--warn); }
.status-pill{ display:inline-flex; align-items:center; gap:.6rem; padding:.5rem 1rem; border-radius:999px;
  background:rgba(34,211,238,.10); border:1px solid rgba(34,211,238,.35); color:#8eeaf8; font-size:.9rem; margin:.4rem 0 .8rem; }
.pulse{ width:9px; height:9px; border-radius:50%; background:var(--p2); box-shadow:0 0 0 0 rgba(34,211,238,.7); animation:pulse 1.4s infinite; }
@keyframes pulse{ 70%{box-shadow:0 0 0 12px rgba(34,211,238,0)} 100%{box-shadow:0 0 0 0 rgba(34,211,238,0)} }

/* score ring + bars */
.ring-wrap{ text-align:center; margin-bottom:1rem; }
.ring{ --v:0; width:150px; height:150px; border-radius:50%; margin:0 auto; display:grid; place-items:center;
  background:conic-gradient(from 0deg, var(--p1), var(--p2) calc(var(--v)*1%), rgba(255,255,255,.08) 0);
  box-shadow:0 0 50px rgba(124,92,255,.35); animation:fill 1.4s cubic-bezier(.2,.8,.2,1) both, float 6s ease-in-out infinite; }
@keyframes fill{ from{--v:0} }
.ring-in{ width:116px; height:116px; border-radius:50%; background:#0b0f22; display:grid; place-items:center; align-content:center; }
.ring-in b{ font-family:'Space Grotesk',sans-serif; font-size:2.2rem; line-height:1; }
.ring-in small{ color:var(--muted); }
.ring-cap{ color:var(--muted); font-size:.8rem; margin-top:.6rem; }
.bar-row{ margin:.45rem 0; font-size:.78rem; color:var(--muted); }
.bar-row .top{ display:flex; justify-content:space-between; margin-bottom:.2rem; }
.bar{ height:7px; border-radius:99px; background:rgba(255,255,255,.07); overflow:hidden; }
.bar > i{ display:block; height:100%; width:var(--w); border-radius:99px; background:linear-gradient(90deg,var(--p1),var(--p2)); animation:grow 1.1s cubic-bezier(.2,.8,.2,1) both; }
@keyframes grow{ from{width:0} }

/* timeline + lists */
.timeline{ list-style:none; padding:0; margin:.4rem 0 0; border-left:2px solid rgba(124,92,255,.35); }
.timeline li{ padding:.25rem 0 .25rem .9rem; position:relative; color:var(--muted); font-size:.8rem; animation:fadeUp .5s ease both; }
.timeline li::before{ content:""; position:absolute; left:-6px; top:.65rem; width:10px; height:10px; border-radius:50%; background:var(--p1); box-shadow:0 0 10px var(--p1); }
.row{ display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:.8rem 1rem; margin-bottom:.55rem;
  background:var(--card); border:1px solid var(--border); border-radius:14px; transition:transform .25s, border-color .25s; animation:fadeUp .5s ease both; }
.row:hover{ transform:translateX(6px); border-color:rgba(124,92,255,.5); }
.row .t{ font-weight:600; } .row .m{ color:var(--muted); font-size:.78rem; }
.score-pill{ min-width:54px; text-align:center; padding:.25rem .6rem; border-radius:10px; font-weight:700; font-size:.85rem;
  background:linear-gradient(135deg,rgba(124,92,255,.25),rgba(34,211,238,.2)); }
.meter{ height:8px; border-radius:99px; background:rgba(255,255,255,.08); overflow:hidden; margin:.35rem 0; }
.meter > i{ display:block; height:100%; width:var(--w); border-radius:99px; background:linear-gradient(90deg,var(--p1),var(--p3)); animation:grow 1.2s ease both; }
.brand{ font-family:'Space Grotesk',sans-serif; font-size:1.35rem; font-weight:700; display:flex; align-items:center; gap:.6rem; margin:.2rem 0 1.2rem; }
.brand .logo{ width:36px; height:36px; border-radius:11px; display:grid; place-items:center;
  background:linear-gradient(135deg,var(--p1),var(--p2)); box-shadow:0 8px 24px rgba(124,92,255,.5); animation:float 5s ease-in-out infinite; }

/* ---------- Streamlit widgets ---------- */
[data-testid="stSidebar"]{ background:linear-gradient(180deg,rgba(14,18,38,.92),rgba(8,10,24,.95)); border-right:1px solid var(--border); backdrop-filter:blur(20px); }
[data-testid="stSidebar"] [role="radiogroup"]{ gap:6px; }
[data-testid="stSidebar"] [role="radiogroup"] label{ padding:.6rem .9rem; border-radius:12px; border:1px solid transparent; transition:all .25s; width:100%; cursor:pointer; }
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child{ display:none; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover{ background:rgba(124,92,255,.14); transform:translateX(5px); }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){
  background:linear-gradient(120deg,rgba(124,92,255,.35),rgba(34,211,238,.18)); border-color:rgba(124,92,255,.5); box-shadow:0 8px 24px rgba(124,92,255,.25); }

.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button{
  border-radius:12px; border:1px solid var(--border); background:var(--card-hi); color:var(--text); font-weight:600;
  transition:transform .2s, box-shadow .25s, border-color .25s; }
.stButton > button:hover, .stDownloadButton > button:hover{ transform:translateY(-3px); border-color:rgba(124,92,255,.7); box-shadow:0 12px 28px rgba(124,92,255,.3); color:#fff; }
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"], button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"]{
  background:linear-gradient(120deg,#7c5cff,#22d3ee,#f472b6); background-size:250% 100%; border:none; color:#fff;
  animation:shine 6s linear infinite; box-shadow:0 10px 30px rgba(124,92,255,.45); }
.stButton > button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover, button[data-testid="stBaseButton-primaryFormSubmit"]:hover{ transform:translateY(-3px) scale(1.02); box-shadow:0 16px 40px rgba(124,92,255,.6); }

.stTextInput input, .stTextArea textarea, .stNumberInput input, div[data-baseweb="select"] > div{
  background:rgba(255,255,255,.05) !important; border:1px solid var(--border) !important; border-radius:12px !important; color:var(--text) !important; transition:all .25s; }
.stTextInput input:focus, .stTextArea textarea:focus{ border-color:var(--p1) !important; box-shadow:0 0 0 3px rgba(124,92,255,.25) !important; }
[data-testid="stForm"]{ border:1px solid var(--border); border-radius:22px; background:var(--card); backdrop-filter:blur(16px); padding:1.4rem; box-shadow:0 10px 40px rgba(0,0,0,.35); }
[data-testid="stExpander"]{ border:1px solid var(--border) !important; border-radius:16px !important; background:var(--card); }
[data-testid="stFileUploaderDropzone"]{ border:2px dashed rgba(124,92,255,.55); border-radius:18px; background:rgba(124,92,255,.07); transition:all .3s; }
[data-testid="stFileUploaderDropzone"]:hover{ background:rgba(124,92,255,.15); transform:scale(1.01); }
.stTabs [data-baseweb="tab-list"]{ gap:6px; }
.stTabs [data-baseweb="tab"]{ border-radius:10px; padding:.4rem 1rem; }
.stTabs [aria-selected="true"]{ background:rgba(124,92,255,.22); }
[data-testid="stAlert"]{ border-radius:14px; }
hr{ border-color:var(--border); }

@media (max-width:900px){ .hero-title{ font-size:2.3rem; } }
@media (prefers-reduced-motion: reduce){ *, *::before, *::after{ animation:none !important; transition:none !important; } }
"""
