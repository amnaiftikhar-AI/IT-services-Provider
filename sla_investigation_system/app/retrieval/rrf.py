def reciprocal_rank_fusion(dense_results, bm25_results, k=60, limit=10):
    scores = {}
    documents = {}
    for result_list in (dense_results, bm25_results):
        for rank, item in enumerate(result_list, start=1):
            key = item["chunk_code"]
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            documents[key] = item
    ranked = sorted(scores, key=scores.get, reverse=True)
    output = []
    for key in ranked[:limit]:
        item = dict(documents[key])
        item["rrf_score"] = scores[key]
        output.append(item)
    return output
