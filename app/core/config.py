import json
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "mysql+pymysql://root:123456@localhost:3306/hermes_kb"

    # Storage
    STORAGE_TYPE: str = "LOCAL"
    LOCAL_STORAGE_PATH: str = "./data/uploads"

    # MinIO (for future use)
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "hermes-kb"
    MINIO_USE_SSL: bool = False

    # Security
    HMAC_TIME_WINDOW_SECONDS: int = 300
    SECRET_KEY: str = ""

    # Storage
    STORAGE_TYPE: str = "LOCAL"
    LOCAL_STORAGE_PATH: str = "./data/uploads"

    # Upload
    UPLOAD_MAX_SIZE_MB: int = 50

    # App
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "dev"

    @property
    def allowed_extensions_list(self) -> List[str]:
        return json.loads(self.ALLOWED_EXTENSIONS)


settings = Settings()
