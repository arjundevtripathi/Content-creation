import hashlib
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["CHROMA_DIR"] = f"{_tmp}/chroma"
os.environ["GROQ_API_KEY"] = "test-key"

import pytest
from chromadb import Documents, EmbeddingFunction, Embeddings
from fastapi.testclient import TestClient

from app.agents.content_agent import ContentAgent
from app.deps import get_agent, get_rag
from app.main import app
from app.services.llm_service import LLMResult, parse_json
from app.services.rag_service import RagService


class FakeEmbedding(EmbeddingFunction[Documents]):
    """Deterministic bag-of-words embeddings so tests never download a model."""

    def __init__(self):
        pass

    def __call__(self, input: Documents) -> Embeddings:
        out = []
        for text in input:
            v = [0.0] * 64
            for w in text.lower().split():
                v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 64] += 1.0
            out.append(v)
        return out

    @staticmethod
    def name() -> str:
        return "fake-bow"

    def get_config(self):
        return {}

    @staticmethod
    def build_from_config(config):
        return FakeEmbedding()


class FakeLLM:
    model, fast_model = "fake-large", "fake-fast"

    def __init__(self):
        self.review_overall = 9  # set low to trigger the revision loop
        self.calls = []

    def _res(self, text):
        return LLMResult(text=text, input_tokens=100, output_tokens=50, latency=0.01)

    def chat(self, system, user, **kw):
        self.calls.append(user[:30])
        return self._res("Generative AI helps developers ship faster. #demo content body " * 5)

    def chat_json(self, system, user, **kw):
        if "Plan a" in user[:100]:
            data = {"title": "Planned Title", "hook": "A hook", "key_points": ["a", "b"], "structure": ["intro"], "cta": "Try it"}
        elif "SEO" in user[:60]:
            data = {"seo_keywords": ["genai", "llm"], "hashtags": ["GenAI", "#LLM"], "meta_description": "desc"}
        else:
            s = self.review_overall
            data = {"scores": {k: s for k in ["relevance", "grammar", "structure", "factual_grounding", "tone", "repetition", "completeness"]},
                    "issues": ["too long"], "suggestions": ["trim"]}
        return data, self._res("{}")

    def stream(self, system, user, usage, **kw):
        usage.update(input_tokens=100, output_tokens=20, latency=0.01)
        yield from ["Hello ", "streamed ", "world"]


@pytest.fixture(scope="session")
def fake_llm():
    return FakeLLM()


@pytest.fixture(scope="session")
def rag():
    return RagService(persist_dir=f"{_tmp}/chroma-test", embedding_function=FakeEmbedding())


@pytest.fixture(scope="session")
def client(fake_llm, rag):
    agent = ContentAgent(fake_llm, rag)
    app.dependency_overrides[get_agent] = lambda: agent
    app.dependency_overrides[get_rag] = lambda: rag
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def auth(client):
    r = client.post("/auth/register", json={"email": "arjun@example.com", "password": "secret123"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
