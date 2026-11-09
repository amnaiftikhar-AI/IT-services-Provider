from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    pinecone_api_key: str = ""
    pinecone_index_name: str = "sla-knowledge"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "openai/gpt-oss-120b"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    scheduler_enabled: bool = False
    scheduler_interval_minutes: int = 1
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
