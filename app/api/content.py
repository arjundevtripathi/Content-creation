import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agents.content_agent import ContentAgent, WRITER_SYSTEM, cost_of
from app.core.security import get_current_user
from app.database.db import Content, Feedback, SessionLocal, User, get_db
from app.deps import get_agent
from app.models.schemas import (ContentOut, ContentUpdate, FeedbackIn, GenerateIn, ReviewIn, RewriteIn)
from app.services import content_service as svc

router = APIRouter(tags=["content"])


def _owned(db: Session, user: User, content_id: int) -> Content:
    item = db.query(Content).filter(Content.id == content_id, Content.user_id == user.id).first()
    if not item:
        raise HTTPException(404, "Content not found")
    return item


@router.post("/generate", response_model=list[ContentOut])
def generate(body: GenerateIn, user: User = Depends(get_current_user),
             db: Session = Depends(get_db), agent: ContentAgent = Depends(get_agent)):
    try:
        return svc.generate(db, user.id, body.model_dump(), agent)
    except RuntimeError as e:
        raise HTTPException(502, str(e))


@router.post("/generate/stream")
def generate_stream(body: GenerateIn, user: User = Depends(get_current_user),
                    agent: ContentAgent = Depends(get_agent)):
    """Server-sent events: plan + retrieve, stream the draft token by token, then review + SEO + save."""
    req, user_id = body.model_dump(), user.id

    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    def events():
        try:
            state = agent.initial_state(user_id, req)
            yield sse({"type": "status", "text": "Planning..."})
            state.update(agent.planner(state))
            yield sse({"type": "status", "text": "Retrieving context..."})
            state.update(agent.retriever(state))
            yield sse({"type": "status", "text": "Writing..."})
            system, prompt = agent.writer_messages(state)
            usage: dict = {}
            parts = []
            for piece in agent.llm.stream(system, prompt, usage):
                parts.append(piece)
                yield sse({"type": "token", "text": piece})
            state["draft"] = "".join(parts).strip()
            state["usage"] = {k: state["usage"][k] + usage[k] for k in usage}
            yield sse({"type": "status", "text": "Quality check and SEO..."})
            state.update(agent.reviewer(state))
            state.update(agent.seo(state))
            db = SessionLocal()
            try:
                item = svc.save_from_state(db, user_id, req, state)
                yield sse({"type": "done", "content": ContentOut.model_validate(item).model_dump(mode="json")})
            finally:
                db.close()
        except Exception as e:  # surface errors to the client instead of dropping the stream
            yield sse({"type": "error", "text": str(e)})

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/rewrite", response_model=ContentOut)
def rewrite(body: RewriteIn, user: User = Depends(get_current_user),
            db: Session = Depends(get_db), agent: ContentAgent = Depends(get_agent)):
    parent = _owned(db, user, body.content_id)
    try:
        return svc.rewrite(db, user.id, parent, body.instruction, agent)
    except RuntimeError as e:
        raise HTTPException(502, str(e))


@router.post("/review")
def review(body: ReviewIn, user: User = Depends(get_current_user), agent: ContentAgent = Depends(get_agent)):
    try:
        result, usage = agent.review_text(body.content, body.content_type, body.topic, body.audience, body.tone)
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    return {**result, "input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"],
            "cost_usd": cost_of(usage)}


@router.get("/content/history", response_model=list[ContentOut])
def history(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
            user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (db.query(Content).filter(Content.user_id == user.id)
            .order_by(Content.created_at.desc(), Content.id.desc()).offset(offset).limit(limit).all())


@router.get("/content/{content_id}", response_model=ContentOut)
def get_content(content_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _owned(db, user, content_id)


@router.patch("/content/{content_id}", response_model=ContentOut)
def update_content(content_id: int, body: ContentUpdate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """Human-in-the-loop: edit the text and/or approve the content."""
    item = _owned(db, user, content_id)
    if body.generated_content is not None:
        item.generated_content = body.generated_content
    if body.status is not None:
        item.status = body.status
    db.commit()
    db.refresh(item)
    return item


@router.delete("/content/{content_id}", status_code=204)
def delete_content(content_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, user, content_id))
    db.commit()


@router.post("/feedback", status_code=201)
def feedback(body: FeedbackIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _owned(db, user, body.content_id)
    db.add(Feedback(content_id=body.content_id, user_id=user.id, rating=body.rating, comment=body.comment))
    db.commit()
    return {"ok": True}


@router.get("/stats")
def stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.user_stats(db, user.id)
