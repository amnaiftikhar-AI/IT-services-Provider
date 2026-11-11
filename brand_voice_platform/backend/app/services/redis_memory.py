import json
from upstash_redis import Redis
from backend.app.core.config import settings

redis_client = Redis(
    url=settings.upstash_redis_rest_url,
    token=settings.upstash_redis_rest_token,
)


def session_key(user_id: int, session_id: int) -> str:
    return f"brandvoice:chat:{user_id}:{session_id}"


def get_recent_messages(user_id: int, session_id: int) -> list[dict]:
    raw = redis_client.get(session_key(user_id, session_id))
    if not raw:
        return []
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def save_recent_messages(user_id: int, session_id: int, messages: list[dict]):
    redis_client.set(
        session_key(user_id, session_id),
        json.dumps(messages[-12:]),
        ex=settings.redis_ttl_seconds,
    )


def clear_session_memory(user_id: int, session_id: int):
    redis_client.delete(session_key(user_id, session_id))
