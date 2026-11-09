from app.retrieval.rrf import reciprocal_rank_fusion

def test_rrf_combines_and_deduplicates():
    dense = [
        {"chunk_code": "a", "content": "A", "metadata": {}},
        {"chunk_code": "b", "content": "B", "metadata": {}}
    ]
    bm25 = [
        {"chunk_code": "b", "content": "B", "metadata": {}},
        {"chunk_code": "c", "content": "C", "metadata": {}}
    ]
    result = reciprocal_rank_fusion(dense, bm25, k=60)
    assert len(result) == 3
    assert result[0]["chunk_code"] == "b"
