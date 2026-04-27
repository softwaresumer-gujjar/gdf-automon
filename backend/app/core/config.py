from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://gdf:gdf_secure_2024@localhost:5432/gdfautomon"
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str = "gdf_backend"
    mqtt_password: str = "backend_secret"
    mqtt_topic_prefix: str = "gdf"
    redis_url: str = "redis://localhost:6379/0"
    vapid_private_key: str = ""
    vapid_public_key: str = ""
    vapid_email: str = "admin@gdfautomon.local"
    fcm_server_key: str = ""
    secret_key: str = "dev_secret_change_in_prod"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    debug: bool = False
    # Twilio (optional — SMS + voice calls)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    # File uploads
    upload_dir: str = "./uploads"
    # SMTP email (password reset + notifications)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "GDF-AutoMon <noreply@gdfautomon.local>"
    smtp_tls: bool = True
    # Frontend URL (used in reset-password email links)
    frontend_url: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
