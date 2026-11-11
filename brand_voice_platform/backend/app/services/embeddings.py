import requests
from backend.app.core.config import settings


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{settings.cloudflare_account_id}/ai/run/{settings.cloudflare_embedding_model}"
    )
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {settings.cloudflare_api_token}"},
        json={"text": texts},
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success", True):
        raise RuntimeError(str(payload.get("errors", "Cloudflare embedding request failed")))
    result = payload.get("result", {})
    vectors = result.get("data")
    if vectors is None:
        vectors = result.get("embeddings")
    if vectors is None:
        raise RuntimeError(f"Unexpected Cloudflare embedding response: {payload}")
    normalized = []
    for item in vectors:
        if isinstance(item, dict):
            item = item.get("embedding") or item.get("vector")
        normalized.append([float(value) for value in item])
    for vector in normalized:
        if len(vector) != settings.embedding_dimensions:
            raise ValueError(
                f"Expected {settings.embedding_dimensions} dimensions but received {len(vector)}. "
                "Check the model response and EMBEDDING_DIMENSIONS."
            )
    return normalized


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
