
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "IT Service Desk - Amna Knowledge Engine"

    database_url: str = "postgresql://localhost/it_services"
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "openai/gpt-oss-120b"

    embedding_model: str = "BAAI/bge-m3"
    faiss_index_path: str = "amna_data/faiss_index"
    upload_dir: str = "amna_data/uploads"

    jwt_secret_key: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    allow_dev_auth: bool = True
    max_upload_mb: int = 20

    model_config = SettingsConfigDict(
        env_file=".env.amna",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
