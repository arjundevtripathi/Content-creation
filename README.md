# ✍️ Content Creation AI

An end-to-end GenAI content platform: **Streamlit** UI → **FastAPI** backend → **LangGraph** agent → **Groq** LLMs, with **ChromaDB** RAG over your own documents, a SQL content history, quality review, SEO tooling, cost tracking and evaluation.

```
User → Streamlit → FastAPI (JWT) → LangGraph agent
                                    planner → retriever (ChromaDB) → writer ⇄ reviewer → SEO
                                    └─ Groq (gpt-oss-120b planner/writer, gpt-oss-20b reviewer/SEO)
                      SQLite/PostgreSQL: users, content history, feedback, documents
```

## Features
- SaaS-style UI: animated gradient background, glass cards with 3D hover tilt, Three.js hero scene, sidebar navigation, dashboard, animated quality ring and score bars (`frontend/styles.py`, `frontend/scene3d.py`, `.streamlit/config.toml`)
- Blog, LinkedIn, Instagram, email and Twitter/X thread generation (tone, audience, length, keywords)
- Multi-step agent: **planner → RAG retriever → writer → quality reviewer → auto-revision loop → SEO**
- RAG knowledge base per user (PDF, DOCX, TXT, MD, CSV, JSON), isolated by user in ChromaDB
- Streaming output, up to 3 versions, one-click rewrite (shorter / more professional / simpler / more engaging)
- Human approval: edit, approve, download
- Quality scores (relevance, grammar, structure, grounding, tone, repetition, completeness), keyword density, Flesch readability
- Token, cost and latency tracking per generation, analytics dashboard, ratings and feedback
- JWT auth, Docker, docker-compose with PostgreSQL, GitHub Actions CI, pytest suite (mocked LLM, no API key needed)
- Offline evaluation script with LLM-as-judge RAG metrics

## Quick start (local, Windows / macOS / Linux)

**Fastest:** run `setup.bat` (Windows) or `./setup.sh` (macOS/Linux), edit `.env`, then run `run.bat` (Windows) or the two commands below. Manual steps:

Use **Python 3.11 or 3.12** (newer pre-release versions often lack wheels for onnxruntime/numpy).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env  → then set GROQ_API_KEY and SECRET_KEY
```

Get a free key at https://console.groq.com, then run two terminals:

```bash
uvicorn app.main:app --reload --port 8000        # API + docs at http://localhost:8000/docs
streamlit run frontend/streamlit_app.py          # UI at http://localhost:8501
```

Register in the UI, upload documents in **Knowledge Base**, then tick **Use my knowledge base** when generating.

> First RAG use downloads Chroma's default embedding model (~80 MB, MiniLM ONNX) once.

## Docker

```bash
docker compose up --build        # API :8000, UI :8501, PostgreSQL, persistent Chroma volume
```

## API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/register`, `/auth/login` | JWT auth |
| POST | `/generate` | Run the agent (`versions` 1-3) |
| POST | `/generate/stream` | SSE: streamed draft, then review + SEO + save |
| POST | `/rewrite` | Rewrite saved content with an instruction |
| POST | `/review` | Quality-score any text |
| GET/PATCH/DELETE | `/content/history`, `/content/{id}` | History, edit/approve, delete |
| POST | `/feedback` | Rating + comment |
| POST/GET/DELETE | `/documents/upload`, `/documents`, `/documents/{id}` | Knowledge base |
| GET | `/stats`, `/health` | Usage analytics, health |

Example:
```json
POST /generate
{"topic": "Generative AI", "content_type": "linkedin", "tone": "professional",
 "audience": "developers", "length": "medium", "keywords": ["GenAI", "RAG"], "use_rag": true}
```

## Project layout
```
app/
  main.py  config.py  deps.py
  api/            auth.py content.py documents.py
  agents/         content_agent.py      # LangGraph graph
  services/       llm_service.py rag_service.py seo_service.py content_service.py prompt_manager.py
  prompts/        planner.txt writer.txt reviewer.txt seo.txt rewrite.txt judge.txt
  models/schemas.py   database/db.py   core/security.py
frontend/streamlit_app.py
evaluation/       run_eval.py test_cases.json
tests/            pytest suite
```
Prompts live in `app/prompts/*.txt`; edit them without touching code.

## Configuration (`.env`)
`GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_FAST_MODEL`, `GROQ_REASONING_EFFORT`, `SECRET_KEY`, `DATABASE_URL` (SQLite default, PostgreSQL supported), `CHROMA_DIR`, `COST_PER_M_INPUT` / `COST_PER_M_OUTPUT` (check current Groq pricing). Quality gate and chunking are tunable in `app/config.py` (`quality_threshold`, `max_revisions`, `chunk_size`, `top_k`).

### Troubleshooting: `model_not_found`
Groq retires models over time. Check https://console.groq.com/docs/models and set `GROQ_MODEL` / `GROQ_FAST_MODEL` in `.env` to a current model ID, then restart the API.

## Tests and evaluation
```bash
pytest -q                                   # no API key required
python -m evaluation.run_eval --user-id 1   # real Groq calls; writes evaluation/results.csv
```
For cases with `"use_rag": true`, the judge reports faithfulness, answer relevancy, context precision and completeness (an LLM-as-judge approximation of RAGAS-style metrics).

## Deploy to AWS EC2 (Docker)
1. Launch an Ubuntu EC2 instance; open ports 22, 8000, 8501 in the security group.
2. `sudo apt install -y docker.io docker-compose-v2`, clone the repo, create `.env` with a strong `SECRET_KEY` and your `GROQ_API_KEY`.
3. `docker compose up -d --build`.
4. For HTTPS, put Nginx or an ALB in front, and replace `allow_origins=["*"]` in `app/main.py` with your UI origin.
5. For CI/CD, extend `.github/workflows/ci.yml` to SSH into the instance and run `git pull && docker compose up -d --build` on pushes to `main`.

## Roadmap mapping
Stage 1 Streamlit + LLM · Stage 2 FastAPI + DB + history · Stage 3 RAG + uploads · Stage 4 LangGraph agent + evaluation + Docker + AWS. All four are included.
