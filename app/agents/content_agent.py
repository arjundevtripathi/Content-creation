"""LangGraph content agent: plan -> retrieve -> write -> review -> (revise) -> SEO."""
import json
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.config import get_settings
from app.services.llm_service import LLMService, estimate_cost
from app.services.prompt_manager import render
from app.services.rag_service import RagService
from app.services.seo_service import seo_stats

FORMAT_GUIDES = {
    "blog": "A blog post in Markdown: H1 title, short intro using the hook, H2 sections, a conclusion and a closing CTA.",
    "linkedin": "A LinkedIn post: strong first-line hook, short 1-2 line paragraphs, a clear CTA, no markdown headings.",
    "instagram": "An Instagram caption: attention-grabbing first line, short friendly lines, a few emojis, a CTA.",
    "email": "A marketing email: 'Subject:' line, 'Preview:' line, greeting, body, CTA, sign-off.",
    "twitter": "A Twitter/X thread of 4-8 numbered tweets, each under 280 characters.",
}
WORD_TARGETS = {"short": 150, "medium": 400, "long": 900}
SCORE_KEYS = ["relevance", "grammar", "structure", "factual_grounding", "tone", "repetition", "completeness"]
WRITER_SYSTEM = "You are a senior content writer. Output only the final content with no preamble or commentary."
REVIEWER_SYSTEM = "You are a strict, fair content reviewer. Respond only with valid JSON."
JSON_SYSTEM = "You are a precise assistant. Respond only with valid JSON."


class AgentState(TypedDict, total=False):
    user_id: int
    topic: str
    content_type: str
    tone: str
    audience: str
    length: str
    keywords: list
    use_rag: bool
    extra_instructions: str
    temperature: float
    plan: dict
    context: str
    sources: list
    draft: str
    review: dict
    needs_revision: bool
    revision_count: int
    seo_keywords: list
    hashtags: list
    meta_description: str
    usage: dict
    trace: list


def new_usage() -> dict:
    return {"input_tokens": 0, "output_tokens": 0, "latency": 0.0}


def _add(usage: dict, res) -> dict:
    return {
        "input_tokens": usage["input_tokens"] + res.input_tokens,
        "output_tokens": usage["output_tokens"] + res.output_tokens,
        "latency": usage["latency"] + res.latency,
    }


class ContentAgent:
    def __init__(self, llm: LLMService, rag: RagService):
        self.llm, self.rag = llm, rag
        self.settings = get_settings()
        self.graph = self._build()

    # ---------- nodes (each returns a partial state update) ----------
    def planner(self, s: AgentState) -> dict:
        has_docs = s.get("use_rag") and self.rag.count(s["user_id"]) > 0
        prompt = render(
            "planner",
            content_type=s["content_type"], topic=s["topic"], audience=s["audience"], tone=s["tone"],
            word_target=WORD_TARGETS[s["length"]], keywords=", ".join(s.get("keywords") or []) or "none",
            extra_instructions=s.get("extra_instructions") or "none",
            context_hint="the user's uploaded documents will be provided" if has_docs else "none",
        )
        plan, res = self.llm.chat_json(JSON_SYSTEM, prompt, max_tokens=800)
        plan.setdefault("title", s["topic"])
        return {
            "plan": plan,
            "usage": _add(s["usage"], res),
            "trace": s["trace"] + [f"planner: planned '{plan['title']}'"],
        }

    def retriever(self, s: AgentState) -> dict:
        if not s.get("use_rag"):
            return {"context": "", "sources": [], "trace": s["trace"] + ["retriever: skipped (RAG off)"]}
        query = " ".join([s["topic"], *(s.get("keywords") or []), s["plan"].get("title", "")])
        hits = self.rag.query(s["user_id"], query)
        if not hits:
            return {"context": "", "sources": [], "trace": s["trace"] + ["retriever: no documents found"]}
        context = "\n\n".join(f"[Source: {h['filename']}]\n{h['text']}" for h in hits)
        sources = sorted({h["filename"] for h in hits})
        return {"context": context, "sources": sources,
                "trace": s["trace"] + [f"retriever: {len(hits)} chunks from {', '.join(sources)}"]}

    def writer_messages(self, s: AgentState) -> tuple[str, str]:
        context_block = (
            f"Reference material (ground your content in this):\n{s['context']}\n" if s.get("context") else ""
        )
        revision_block = ""
        if s.get("needs_revision") and s.get("draft"):
            fb = s["review"]
            revision_block = (
                "Your previous draft:\n" + s["draft"] +
                "\n\nReviewer issues:\n- " + "\n- ".join(fb.get("issues", []) or ["none"]) +
                "\n\nReviewer suggestions:\n- " + "\n- ".join(fb.get("suggestions", []) or ["none"]) +
                "\n\nWrite an improved version that fixes every issue.\n"
            )
        prompt = render(
            "writer",
            content_type=s["content_type"], topic=s["topic"], audience=s["audience"], tone=s["tone"],
            word_target=WORD_TARGETS[s["length"]], keywords=", ".join(s.get("keywords") or []) or "none",
            extra_instructions=s.get("extra_instructions") or "none",
            format_guide=FORMAT_GUIDES[s["content_type"]],
            plan=json.dumps(s["plan"], indent=2),
            context_block=context_block, revision_block=revision_block,
        )
        return WRITER_SYSTEM, prompt

    def writer(self, s: AgentState) -> dict:
        revising = bool(s.get("needs_revision") and s.get("draft"))
        system, prompt = self.writer_messages(s)
        res = self.llm.chat(system, prompt, temperature=s.get("temperature", 0.7), max_tokens=3000)
        return {
            "draft": res.text.strip(),
            "revision_count": s.get("revision_count", 0) + (1 if revising else 0),
            "usage": _add(s["usage"], res),
            "trace": s["trace"] + [f"writer: {'revised' if revising else 'wrote'} draft ({len(res.text.split())} words)"],
        }

    def reviewer(self, s: AgentState) -> dict:
        review, usage = self.review_text(
            s["draft"], s["content_type"], s["topic"], s["audience"], s["tone"], s.get("context", "")
        )
        threshold = self.settings.quality_threshold
        needs = review["overall"] < threshold
        return {
            "review": review,
            "needs_revision": needs,
            "usage": {k: s["usage"][k] + usage[k] for k in usage},
            "trace": s["trace"] + [f"reviewer: overall {review['overall']}/10" + (" -> revise" if needs else " -> pass")],
        }

    def review_text(self, content, content_type, topic, audience, tone, context="") -> tuple[dict, dict]:
        prompt = render(
            "reviewer", content_type=content_type, topic=topic, audience=audience, tone=tone,
            content=content,
            context_block=f"Reference material:\n{context}\n" if context else "",
        )
        data, res = self.llm.chat_json(REVIEWER_SYSTEM, prompt, model=self.llm.fast_model, max_tokens=700)
        raw = data.get("scores") or {}
        scores = {}
        for k in SCORE_KEYS:
            try:
                scores[k] = max(1.0, min(10.0, float(raw.get(k, 7))))
            except (TypeError, ValueError):
                scores[k] = 7.0
        review = {
            "scores": scores,
            "overall": round(sum(scores.values()) / len(scores), 1),
            "issues": [str(i) for i in data.get("issues", [])][:6],
            "suggestions": [str(i) for i in data.get("suggestions", [])][:6],
        }
        return review, {"input_tokens": res.input_tokens, "output_tokens": res.output_tokens, "latency": res.latency}

    def seo(self, s: AgentState) -> dict:
        prompt = render(
            "seo", content_type=s["content_type"], topic=s["topic"],
            keywords=", ".join(s.get("keywords") or []) or "none", content=s["draft"],
        )
        data, res = self.llm.chat_json(JSON_SYSTEM, prompt, model=self.llm.fast_model, max_tokens=500)
        hashtags = [h if h.startswith("#") else f"#{h}" for h in map(str, data.get("hashtags", []))][:8]
        review = dict(s.get("review", {}))
        review["seo_stats"] = seo_stats(s["draft"], s.get("keywords") or [])
        return {
            "seo_keywords": [str(k) for k in data.get("seo_keywords", [])][:8],
            "hashtags": hashtags,
            "meta_description": str(data.get("meta_description", ""))[:200],
            "review": review,
            "usage": _add(s["usage"], res),
            "trace": s["trace"] + ["seo: keywords, hashtags and meta description generated"],
        }

    # ---------- graph ----------
    def _route_after_review(self, s: AgentState) -> str:
        if s.get("needs_revision") and s.get("revision_count", 0) < self.settings.max_revisions:
            return "writer"
        return "seo"

    def _build(self):
        g = StateGraph(AgentState)
        g.add_node("planner", self.planner)
        g.add_node("retriever", self.retriever)
        g.add_node("writer", self.writer)
        g.add_node("reviewer", self.reviewer)
        g.add_node("seo", self.seo)
        g.set_entry_point("planner")
        g.add_edge("planner", "retriever")
        g.add_edge("retriever", "writer")
        g.add_edge("writer", "reviewer")
        g.add_conditional_edges("reviewer", self._route_after_review, {"writer": "writer", "seo": "seo"})
        g.add_edge("seo", END)
        return g.compile()

    def initial_state(self, user_id: int, req: dict, temperature: float = 0.7) -> AgentState:
        return AgentState(
            user_id=user_id, topic=req["topic"], content_type=req["content_type"], tone=req["tone"],
            audience=req["audience"], length=req["length"], keywords=req.get("keywords", []),
            use_rag=req.get("use_rag", False), extra_instructions=req.get("extra_instructions", ""),
            temperature=temperature, revision_count=0, needs_revision=False,
            usage=new_usage(), trace=[], context="", sources=[],
        )

    def run(self, user_id: int, req: dict, temperature: float = 0.7) -> AgentState:
        return self.graph.invoke(self.initial_state(user_id, req, temperature))


def cost_of(usage: dict) -> float:
    return estimate_cost(usage["input_tokens"], usage["output_tokens"])
