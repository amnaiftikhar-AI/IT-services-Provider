from supabase import create_client
from backend.app.core.config import settings

client = create_client(settings.supabase_url, settings.supabase_service_role_key)


def upload_document(path: str, content: bytes, content_type: str):
    return client.storage.from_(settings.supabase_bucket).upload(
        path=path,
        file=content,
        file_options={"content-type": content_type, "upsert": "true"},
    )
