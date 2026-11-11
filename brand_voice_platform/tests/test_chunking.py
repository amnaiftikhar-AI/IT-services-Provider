from backend.app.services.chunking import split_document


def test_split_document_returns_chunks():
    text = ("Brand tone should be friendly. " * 300) + "\n## Formatting\nUse short paragraphs."
    chunks = split_document(text, chunk_size=500, chunk_overlap=50)
    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)
