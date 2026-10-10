from app.services.rag_service import chunk_text, extract_text
from app.services.seo_service import seo_stats
from app.services.llm_service import parse_json


def test_chunking_respects_size():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 60 for i in range(10))
    chunks = chunk_text(text, size=500, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 600 for c in chunks)


def test_chunk_empty():
    assert chunk_text("   ") == []


def test_extract_text_txt_and_unsupported():
    assert "hello" in extract_text("a.txt", b"hello")
    try:
        extract_text("a.exe", b"x")
        assert False
    except ValueError:
        pass


def test_rag_isolation_and_delete(rag):
    rag.add_document(1, 10, "a.txt", "Our product Nimbus syncs files across devices instantly.")
    rag.add_document(2, 20, "b.txt", "Secret roadmap for another user about quantum widgets.")
    hits = rag.query(1, "Nimbus file sync")
    assert hits and all(h["filename"] == "a.txt" for h in hits)
    assert rag.count(2) == 1
    rag.delete_document(1, 10)
    assert rag.count(1) == 0 and rag.query(1, "Nimbus") == []


def test_seo_stats():
    s = seo_stats("Generative AI is great. Generative AI is fun.", ["generative ai", "rag"])
    assert s["keyword_density_pct"]["generative ai"] > 0 and "rag" in s["missing_keywords"]


def test_parse_json_handles_fences():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json("no json here") == {}
