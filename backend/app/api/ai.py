"""Admin AI settings routes — provider selection, API key management, health check."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.db import get_session
from app.llm.base import HealthCheckResult
from app.llm.encryption import SecretStore
from app.llm.manager import ProviderManager
from app.models.models import LLMConfig, User
from app.repositories import AuditLogRepository
from app.schemas.schemas import AIConfigReq, AIConfigResp, AIHealthResp
from app.security.auth import require_role

settings = get_settings()
logger = logging.getLogger("accel.admin.ai")

router = APIRouter(prefix="/admin/ai", tags=["admin-ai"])

# Singleton manager (rebuilt when config changes)
_manager: ProviderManager | None = None


def _get_manager(session: Session) -> ProviderManager:
    global _manager
    if _manager is None:
        _manager = ProviderManager()
    return _manager


def _audit(
    session: Session,
    actor: User | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    before_hash: str | None = None,
    after_hash: str | None = None,
) -> None:
    repo = AuditLogRepository(session)
    repo.create(
        actor_id=actor.user_id if actor else None,
        actor_role=actor.role if actor else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        before_hash=before_hash,
        after_hash=after_hash,
    )


def _config_to_resp(config: LLMConfig, secret_store: SecretStore) -> AIConfigResp:
    return AIConfigResp(
        provider=config.provider,
        base_url=config.base_url,
        model=config.model,
        vision_model=config.vision_model,
        vision_enabled=config.vision_enabled,
        api_key_masked=secret_store.mask(config.api_key_encrypted),
        timeout_seconds=config.timeout_seconds,
        max_retries=config.max_retries,
        circuit_breaker_threshold=config.circuit_breaker_threshold,
        circuit_breaker_timeout_seconds=config.circuit_breaker_timeout_seconds,
        is_active=config.is_active,
    )


@router.get("/settings", response_model=AIConfigResp)
def get_ai_settings(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(["admin"])),
):
    config = session.exec(select(LLMConfig).where(LLMConfig.is_active == True)).first()  # noqa: E712
    if not config:
        # Return defaults
        return AIConfigResp(
            provider=settings.llm_provider,
            base_url=settings.ollama_base_url,
            model=settings.llm_model,
            vision_model=settings.llm_vision_model,
            vision_enabled=settings.llm_vision_enabled,
            api_key_masked="",
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
            circuit_breaker_threshold=settings.llm_circuit_breaker_threshold,
            circuit_breaker_timeout_seconds=settings.llm_circuit_breaker_timeout_seconds,
            is_active=True,
        )
    return _config_to_resp(config, SecretStore(settings.app_encryption_key))


@router.post("/settings", response_model=AIConfigResp)
def save_ai_settings(
    req: AIConfigReq,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(["admin"])),
):
    secret_store = SecretStore(settings.app_encryption_key)
    # Deactivate existing
    existing = session.exec(select(LLMConfig).where(LLMConfig.is_active == True)).first()  # noqa: E712
    if existing:
        existing.is_active = False
        session.add(existing)

    api_key_encrypted = None
    if req.api_key:
        api_key_encrypted = secret_store.encrypt(req.api_key)

    config = LLMConfig(
        provider=req.provider,
        base_url=req.base_url,
        model=req.model,
        vision_model=req.vision_model,
        vision_enabled=req.vision_enabled,
        api_key_encrypted=api_key_encrypted,
        timeout_seconds=req.timeout_seconds,
        max_retries=req.max_retries,
        circuit_breaker_threshold=req.circuit_breaker_threshold,
        circuit_breaker_timeout_seconds=req.circuit_breaker_timeout_seconds,
        is_active=True,
    )
    session.add(config)
    session.commit()
    session.refresh(config)

    _audit(
        session,
        current_user,
        "ai_settings_change",
        resource_type="llm_config",
        resource_id=str(config.id),
        ip_address=request.client.host if request.client else None,
        after_hash=f"{req.provider}:{req.model}",
    )

    # Rebuild manager
    global _manager
    _manager = None

    return _config_to_resp(config, secret_store)


@router.get("/health", response_model=list[AIHealthResp])
def ai_health(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(["admin"])),
):
    manager = _get_manager(session)
    results = manager.health_check_all()
    return [
        AIHealthResp(
            provider=r.provider,
            model=r.model,
            healthy=r.healthy,
            latency_ms=r.latency_ms,
            error=r.error,
        )
        for r in results.values()
    ]


@router.post("/test", response_model=AIHealthResp)
def test_ai_connection(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(["admin"])),
):
    """Test the currently configured provider with a sample prompt."""
    manager = _get_manager(session)
    # Send a harmless test message
    try:
        response = manager.chat(
            messages=[{"role": "user", "content": "Say 'hello' in one word."}],
            redact_pii=True,
        )
        # Get health for the active provider
        health_results = manager.health_check_all()
        active = manager.active_provider
        result = health_results.get(active)
        if not result:
            result = HealthCheckResult(
                healthy=True,
                latency_ms=response.latency_ms,
                error=None,
                provider=active,
                model=response.model,
            )
        return AIHealthResp(
            provider=result.provider,
            model=result.model,
            healthy=result.healthy,
            latency_ms=result.latency_ms,
            error=result.error,
        )
    except Exception as err:
        logger.error("AI test failed: %s", err)
        return AIHealthResp(
            provider=manager.active_provider,
            model=settings.llm_model,
            healthy=False,
            latency_ms=None,
            error=str(err),
        )


# Rebuild manager when settings change — callable from other modules
def rebuild_manager() -> None:
    global _manager
    _manager = None
