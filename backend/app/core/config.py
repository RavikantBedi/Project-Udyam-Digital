from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    app_name: str = "Accel Business - Udyam Digital"
    app_env: str = "dev"
    database_url: str = "sqlite:///./db/app.db"
    anthropic_api_key: str = ""
    demo_today: str = "2026-07-15"
    data_dir: str = ""
    upload_dir: str = "./uploads"
    backend_url: str = "http://localhost:8000"

    # Notification & Gateway Settings
    jwt_secret: str = "accel-udyam-secret-key-2026"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "alerts@accelbusiness.in"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_sms_from: str = ""
    twilio_whatsapp_from: str = ""
    whatsapp_webhook_token: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def get_data_dir() -> str:
    s = get_settings()
    if s.data_dir and os.path.exists(s.data_dir):
        return s.data_dir
    for cand in [
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"),
        "d:/Project_Airtel_2.0/data",
        "/data",
        "../data",
        "./data",
        "../../data",
    ]:
        cand = os.path.normpath(cand)
        if os.path.exists(cand):
            return cand
    return "./data"
