from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents.content_agent import ContentAgent, cost_of
from app.database.db import Content, Feedback
from app.services.prompt_manager import render

REWRITE_SYSTEM = "You are an expert editor. Output only the rewritten content."


def save_from_state(db: Session, user_id: int, req: dict, state: dict, parent_id: int | None = None) -> Content:
    usage = state["usage"]
    item = Content(
        user_id=user_id,
        topic=req["topic"], content_type=req["content_type"], tone=req["tone"],
        audience=req["audience"], length=req["length"], keywords=req.get("keywords", []),
        title=state.get("plan", {}).get("title", req["topic"])[:500],
        generated_content=state["draft"],
        hashtags=state.get("hashtags", []), seo_keywords=state.get("seo_keywords", []),
        meta_description=state.get("meta_description", ""),
        plan=state.get("plan", {}), review=state.get("review", {}),
        sources=state.get("sources", []), trace=state.get("trace", []),
        parent_id=parent_id,
        input_tokens=usage["input_tokens"], output_tokens=usage["output_tokens"],
        cost_usd=cost_of(usage), latency_s=round(usage["latency"], 2),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def generate(db: Session, user_id: int, req: dict, agent: ContentAgent) -> list[Content]:
    results = []
    for v in range(req.get("versions", 1)):
        state = agent.run(user_id, req, temperature=min(0.6 + 0.15 * v, 0.95))
        results.append(save_from_state(db, user_id, req, state))
    return results


def rewrite(db: Session, user_id: int, parent: Content, instruction: str, agent: ContentAgent) -> Content:
    prompt = render("rewrite", content_type=parent.content_type, instruction=instruction, content=parent.generated_content)
    res = agent.llm.chat(REWRITE_SYSTEM, prompt, temperature=0.6, max_tokens=3000)
    review, rv_usage = agent.review_text(
        res.text, parent.content_type, parent.topic, parent.audience, parent.tone
    )
    usage = {
        "input_tokens": res.input_tokens + rv_usage["input_tokens"],
        "output_tokens": res.output_tokens + rv_usage["output_tokens"],
        "latency": res.latency + rv_usage["latency"],
    }
    req = dict(topic=parent.topic, content_type=parent.content_type, tone=parent.tone,
               audience=parent.audience, length=parent.length, keywords=parent.keywords)
    state = {
        "draft": res.text.strip(), "plan": {**parent.plan, "rewrite_instruction": instruction},
        "hashtags": parent.hashtags, "seo_keywords": parent.seo_keywords,
        "meta_description": parent.meta_description, "review": review, "sources": parent.sources,
        "trace": [f"rewrite: {instruction}"], "usage": usage,
    }
    return save_from_state(db, user_id, req, state, parent_id=parent.id)


def user_stats(db: Session, user_id: int) -> dict:
    row = db.query(
        func.count(Content.id), func.coalesce(func.sum(Content.input_tokens), 0),
        func.coalesce(func.sum(Content.output_tokens), 0), func.coalesce(func.sum(Content.cost_usd), 0.0),
        func.coalesce(func.avg(Content.latency_s), 0.0),
    ).filter(Content.user_id == user_id).one()
    avg_rating = db.query(func.avg(Feedback.rating)).filter(Feedback.user_id == user_id).scalar()
    approved = db.query(func.count(Content.id)).filter(Content.user_id == user_id, Content.status == "approved").scalar()
    by_type = dict(
        db.query(Content.content_type, func.count(Content.id))
        .filter(Content.user_id == user_id).group_by(Content.content_type).all()
    )
    return {
        "total_generations": row[0], "approved": approved,
        "input_tokens": int(row[1]), "output_tokens": int(row[2]),
        "total_cost_usd": round(float(row[3]), 4), "avg_latency_s": round(float(row[4]), 2),
        "avg_rating": round(float(avg_rating), 2) if avg_rating else None,
        "by_content_type": by_type,
    }
