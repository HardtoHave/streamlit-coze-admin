from pydantic_settings import BaseSettings  # ✅ 旧版写在 pydantic 中，现在是单独包
from pydantic import Field


class Settings(BaseSettings):
    mongodb_url: str = Field(..., env="MONGODB_URL")
    database_name: str = Field(default="coze", env="DATABASE_NAME")
    admin_password_hash: str = Field(..., env="ADMIN_PASSWORD_HASH")
    cookie_key: str = Field(..., env="COOKIE_KEY")
    cookie_name: str = Field(default="coze_admin_auth_cookie", env="COOKIE_NAME")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
