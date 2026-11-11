from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Personalized Brand Voice Platform"
    secret_key: str
    access_token_expire_minutes: int = 60
    database_url: str
    groq_api_key: str
    groq_model: str = "openai/gpt-oss-120b"
    cloudflare_account_id: str
    cloudflare_api_token: str
    cloudflare_embedding_model: str = "@cf/baai/bge-m3"
    embedding_dimensions: int = 1024
    supabase_url: str
    supabase_service_role_key: str
    supabase_bucket: str = "brand-voice-documents"
    upstash_redis_rest_url: str
    upstash_redis_rest_token: str
    redis_ttl_seconds: int = 86400
    max_upload_mb: int = 15

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
