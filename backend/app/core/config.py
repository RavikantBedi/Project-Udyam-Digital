"""Application configuration — all values from environment variables."""
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "Accel Business - Udyam Digital"
    app_env: str = Field("dev", description="dev | staging | production")
    database_url: str = Field("sqlite:///./db/app.db", description="SQLAlchemy database URL")
    demo_today: str = Field("2026-07-15", description="Reference date for demo logic (YYYY-MM-DD)")
    data_dir: str = Field("./data", description="Path to data directory")
    upload_dir: str = Field("./uploads", description="Path to upload directory")
    backend_url: str = Field("http://localhost:8000")
    frontend_url: str = Field("http://localhost:5173")

    # Security
    jwt_secret: str = Field(..., description="JWT signing secret — required, no default")
    app_encryption_key: str = Field(..., description="32-byte base64 encryption key — required")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # CORS — comma separated list of allowed origins
    cors_origins: str = Field("http://localhost:5173,http://127.0.0.1:5173")

    # Rate limiting
    rate_limit_signin_per_min: int = Field(5, description="signin attempts per minute per IP")
    rate_limit_signup_per_min: int = Field(3, description="signup attempts per minute per IP")
    rate_limit_otp_per_min: int = Field(5, description="OTP requests per minute per target")
    rate_limit_advisor_per_min: int = Field(30, description="advisor messages per minute per IP")
    lockout_after_failures: int = Field(5, description="failed logins before lockout")
    lockout_minutes: int = Field(15, description="account lockout duration in minutes")

    # OTP
    otp_expire_minutes: int = Field(5, description="OTP expiry in minutes")
    otp_max_attempts: int = Field(5, description="max OTP attempts before lockout")
    otp_dev_mode: bool = Field(True, description="dev mode — log OTP codes instead of sending")
    twilio_verify_service_sid: str = Field("", description="Twilio Verify service SID")

    # Admin seed (dev only)
    admin_email: str = Field("admin@accelbusiness.in", description="Admin user email")
    admin_password: str = Field("AccelAdmin2026!", description="Admin user password")
    sales_email: str = Field("sales@accelbusiness.in", description="Demo sales user email")
    sales_password: str = Field("AccelSales2026!", description="Demo sales user password")
    partner_email: str = Field("partner@accelbusiness.in", description="Demo partner user email")
    partner_password: str = Field("AccelPartner2026!", description="Demo partner user password")

    # Notifications
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

    # LLM
    anthropic_api_key: str = ""
    llm_provider: str = Field("offline", description="offline | anthropic | openai | ollama")
    openai_api_key: str = ""
    openai_base_url: str = ""
    ollama_base_url: str = Field("http://localhost:11434")
    llm_model: str = Field("qwen2.5:7b-instruct", description="Default model name")
    llm_vision_model: str | None = Field(None, description="Vision model name (defaults to llm_model)")
    llm_vision_enabled: bool = Field(False, description="Enable vision/document extraction via LLM")
    llm_timeout_seconds: int = Field(60, description="LLM request timeout in seconds")
    llm_max_retries: int = Field(2, description="Max LLM retries")
    llm_circuit_breaker_threshold: int = Field(3, description="Circuit breaker failure threshold")
    llm_circuit_breaker_timeout_seconds: int = Field(60, description="Circuit breaker recovery timeout (seconds)")

    @field_validator("jwt_secret")
    @classmethod
    def _jwt_secret_not_default(cls, v: str, info) -> str:
        if info.data.get("app_env") == "production" and (
            not v or v == "accel-udyam-secret-key-2026"
        ):
            raise ValueError("JWT_SECRET must be set to a non-default value in production")
        return v

    @field_validator("app_encryption_key")
    @classmethod
    def _enc_key_not_default(cls, v: str, info) -> str:
        if info.data.get("app_env") == "production" and (
            not v or v == "accel-udyam-enc-key-2026"
        ):
            raise ValueError("APP_ENCRYPTION_KEY must be set to a non-default value in production")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_data_dir() -> str:
    import os

    s = get_settings()
    d = s.data_dir
    if d and os.path.exists(d):
        return d
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
