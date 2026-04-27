import json
import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file() -> str:
    """根据 ENVIRONMENT 环境变量选择对应的 .env 文件"""
    env = os.getenv("ENVIRONMENT", "dev")
    env_file_map = {
        "local_prod": ".env.local_prod",
        "dev": ".env.dev",
    }
    return env_file_map.get(env, ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=get_env_file(), extra="ignore")

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
    MCP_ALLOWED_ORIGINS: str = '["http://localhost", "http://127.0.0.1"]'

    @property
    def allowed_extensions_list(self) -> List[str]:
        return json.loads(self.ALLOWED_EXTENSIONS)

    @property
    def mcp_allowed_origins_list(self) -> List[str]:
        return json.loads(self.MCP_ALLOWED_ORIGINS)


settings = Settings()
