from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, content, documents
from app.config import get_settings
from app.database.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Content Creation AI", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(content.router)
app.include_router(documents.router)


@app.get("/health", tags=["meta"])
def health():
    s = get_settings()
    return {"status": "ok", "groq_configured": bool(s.groq_api_key), "model": s.groq_model}
