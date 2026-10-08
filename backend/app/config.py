from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "锦安特种设备检测"
    database_url: str = "sqlite:///./ailitewms.db"
    jwt_secret: str = "change-this-secret-in-production"
    access_token_minutes: int = 480
    initial_admin_username: str = "admin"
    initial_admin_password: str = "Admin@123456"
    second_admin_username: str = "admin_backup"
    second_admin_password: str = "BackupAdmin@123456"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
