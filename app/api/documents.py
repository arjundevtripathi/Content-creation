from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import get_current_user
from app.database.db import Document, User, get_db
from app.deps import get_rag
from app.models.schemas import DocumentOut
from app.services.rag_service import RagService, extract_text

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    rag: RagService = Depends(get_rag),
):
    data = await file.read()
    if len(data) > get_settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {get_settings().max_upload_mb} MB")
    try:
        text = extract_text(file.filename or "upload.txt", data)
    except ValueError as e:
        raise HTTPException(415, str(e))
    if not text.strip():
        raise HTTPException(422, "No extractable text found in the file")
    doc = Document(user_id=user.id, filename=file.filename or "upload.txt")
    db.add(doc)
    db.flush()
    doc.chunks = rag.add_document(user.id, doc.id, doc.filename, text)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Document).filter(Document.user_id == user.id).order_by(Document.id.desc()).all()


@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    rag: RagService = Depends(get_rag),
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == user.id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    rag.delete_document(user.id, doc.id)
    db.delete(doc)
    db.commit()
