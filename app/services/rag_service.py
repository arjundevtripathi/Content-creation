import io
import re
from pathlib import Path

import chromadb

from app.config import get_settings


def chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    """Paragraph-aware chunking with character overlap."""
    text = re.sub(r"\n{3,}", "\n\n", text.replace("\r", "")).strip()
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, buf = [], ""
    for p in paragraphs:
        while len(p) > size:  # split oversized paragraphs
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.append(p[:size])
            p = p[size - overlap :]
        if len(buf) + len(p) + 2 <= size:
            buf = f"{buf}\n\n{p}".strip()
        else:
            if buf:
                chunks.append(buf)
            tail = buf[-overlap:] if buf and overlap else ""
            buf = f"{tail}\n\n{p}".strip() if tail else p
    if buf:
        chunks.append(buf)
    return chunks


def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    if ext == ".docx":
        from docx import Document as Docx

        return "\n\n".join(p.text for p in Docx(io.BytesIO(data)).paragraphs)
    if ext in {".txt", ".md", ".csv", ".json"}:
        return data.decode("utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type '{ext}'. Use PDF, DOCX, TXT, MD, CSV or JSON.")


class RagService:
    """ChromaDB-backed knowledge base. One collection; every chunk is tagged with its owner."""

    def __init__(self, persist_dir: str | None = None, embedding_function=None):
        s = get_settings()
        self.chunk_size, self.overlap, self.top_k = s.chunk_size, s.chunk_overlap, s.top_k
        self.client = chromadb.PersistentClient(path=persist_dir or s.chroma_dir)
        kwargs = {"embedding_function": embedding_function} if embedding_function else {}
        self.collection = self.client.get_or_create_collection(
            "knowledge_base", metadata={"hnsw:space": "cosine"}, **kwargs
        )

    def add_document(self, user_id: int, doc_id: int, filename: str, text: str) -> int:
        chunks = chunk_text(text, self.chunk_size, self.overlap)
        if not chunks:
            return 0
        self.collection.add(
            ids=[f"{doc_id}-{i}" for i in range(len(chunks))],
            documents=chunks,
            metadatas=[
                {"user_id": user_id, "doc_id": doc_id, "filename": filename, "chunk": i}
                for i in range(len(chunks))
            ],
        )
        return len(chunks)

    def count(self, user_id: int) -> int:
        return len(self.collection.get(where={"user_id": user_id}, include=[])["ids"])

    def query(self, user_id: int, query: str, k: int | None = None) -> list[dict]:
        total = self.count(user_id)
        if total == 0:
            return []
        res = self.collection.query(
            query_texts=[query],
            n_results=min(k or self.top_k, total),
            where={"user_id": user_id},
        )
        return [
            {"text": doc, "filename": meta["filename"], "distance": dist}
            for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
        ]

    def delete_document(self, user_id: int, doc_id: int) -> None:
        self.collection.delete(where={"$and": [{"user_id": user_id}, {"doc_id": doc_id}]})
