"""Admin router — back-office lead management, assignments, audit log."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import Session

from app.core.db import get_session
from app.models.models import User
from app.schemas.schemas import (
    AuditLogResp,
    LeadAssignmentCreateReq,
    LeadAssignmentOutcomeReq,
    LeadAssignmentResp,
    LeadResp,
)
from app.security.auth import get_current_user, require_role
from app.services.admin_service import AdminService

router = APIRouter(tags=["admin"])


@router.get("/leads", response_model=list[LeadResp])
def admin_leads(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    service = AdminService(session)
    leads = service.list_leads(
        actor_user_id=current_user.user_id,
        actor_role=current_user.role,
    )
    result = []
    for lead in leads:
        # PII masking for partners
        if current_user.role == "partner":
            result.append(
                LeadResp(
                    lead_id=lead.lead_id,
                    business_name=lead.business_name,
                    business_type=lead.business_type,
                    segment=lead.segment,
                    city=lead.city,
                    language=lead.preferred_language,
                    bundle_drafted="",
                    propensity_score=0,
                    reasons=[],
                    ai_summary="",
                    suggested_action="",
                    stage=lead.stage_reached,
                    drop_reason=lead.drop_reason,
                    has_gstin="***MASKED***",
                )
            )
        else:
            result.append(
                LeadResp(
                    lead_id=lead.lead_id,
                    business_name=lead.business_name,
                    business_type=lead.business_type,
                    segment=lead.segment,
                    city=lead.city,
                    language=lead.preferred_language,
                    bundle_drafted="",
                    propensity_score=0,
                    reasons=[],
                    ai_summary="",
                    suggested_action="",
                    stage=lead.stage_reached,
                    drop_reason=lead.drop_reason,
                    has_gstin=lead.has_gstin,
                )
            )
    return result


@router.post(
    "/leads/{lead_id}/assign",
    response_model=LeadAssignmentResp,
    status_code=status.HTTP_201_CREATED,
)
def admin_assign_lead(
    lead_id: str,
    req: LeadAssignmentCreateReq,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    service = AdminService(session)
    try:
        assignment = service.assign_lead(
            actor_user_id=current_user.user_id,
            actor_role=current_user.role,
            lead_id=lead_id,
            assignee_type=req.assignee_type,
            assignee_id=req.assignee_id,
            attribution_tag=req.attribution_tag,
            outcome=req.outcome,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from None
    except PermissionError as err:
        raise HTTPException(status_code=403, detail=str(err)) from None
    return LeadAssignmentResp.model_validate(assignment)


@router.patch(
    "/assignments/{assignment_id}/outcome", response_model=LeadAssignmentResp
)
def admin_update_assignment_outcome(
    assignment_id: int,
    req: LeadAssignmentOutcomeReq,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    service = AdminService(session)
    try:
        assignment = service.update_assignment_outcome(
            actor_user_id=current_user.user_id,
            actor_role=current_user.role,
            assignment_id=assignment_id,
            outcome=req.outcome,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from None
    except PermissionError as err:
        raise HTTPException(status_code=403, detail=str(err)) from None
    return LeadAssignmentResp.model_validate(assignment)


@router.get("/audit-log", response_model=list[AuditLogResp])
def admin_audit_log(
    action: str | None = Query(None),
    actor_role: str | None = Query(None),
    limit: int = Query(100, le=500),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(["admin"])),
):
    service = AdminService(session)
    logs = service.list_audit_log(
        actor_user_id=current_user.user_id,
        actor_role=current_user.role,
        action=action,
        actor_role_filter=actor_role,
        limit=limit,
    )
    return [AuditLogResp.model_validate(log) for log in logs]


@router.get("/roles/matrix", response_model=list[dict])
def admin_role_matrix():
    """Return the role × endpoint access matrix for documentation."""
    return [
        {"endpoint": "/api/auth/signup", "anonymous": True, "owner": False,
         "sales": False, "partner": False, "admin": False},
        {"endpoint": "/api/auth/signin", "anonymous": True, "owner": False,
         "sales": False, "partner": False, "admin": False},
        {"endpoint": "/api/auth/refresh", "anonymous": False, "owner": True,
         "sales": True, "partner": True, "admin": True},
        {"endpoint": "/api/auth/signout", "anonymous": False, "owner": True,
         "sales": True, "partner": True, "admin": True},
        {"endpoint": "/api/auth/signout-all", "anonymous": False, "owner": True,
         "sales": True, "partner": True, "admin": True},
        {"endpoint": "/api/auth/me", "anonymous": False, "owner": True,
         "sales": True, "partner": True, "admin": True},
        {"endpoint": "/api/auth/change-password", "anonymous": False,
         "owner": True, "sales": True, "partner": True, "admin": True},
        {"endpoint": "/api/auth/forgot-password", "anonymous": True,
         "owner": False, "sales": False, "partner": False, "admin": False},
        {"endpoint": "/api/auth/reset-password", "anonymous": True,
         "owner": False, "sales": False, "partner": False, "admin": False},
        {"endpoint": "/api/auth/otp/send", "anonymous": True,
         "owner": False, "sales": False, "partner": False, "admin": False},
        {"endpoint": "/api/auth/otp/verify", "anonymous": True,
         "owner": False, "sales": False, "partner": False, "admin": False},
        {"endpoint": "/api/admin/users", "anonymous": False,
         "owner": False, "sales": False, "partner": False, "admin": True},
        {"endpoint": "/api/admin/leads", "anonymous": False,
         "owner": False, "sales": True, "partner": True, "admin": True},
        {"endpoint": "/api/admin/audit-log", "anonymous": False,
         "owner": False, "sales": False, "partner": False, "admin": True},
        {"endpoint": "/api/catalogue", "anonymous": True,
         "owner": True, "sales": True, "partner": True, "admin": True},
        {"endpoint": "/api/advisor/message", "anonymous": True,
         "owner": True, "sales": True, "partner": True, "admin": True},
        {"endpoint": "/api/lookup/gstin/{gstin}", "anonymous": True,
         "owner": True, "sales": True, "partner": True, "admin": True},
        {"endpoint": "/api/lookup/udyam/{number}", "anonymous": True,
         "owner": True, "sales": True, "partner": True, "admin": True},
        {"endpoint": "/api/orders", "anonymous": False,
         "owner": True, "sales": False, "partner": False, "admin": False},
        {"endpoint": "/api/orders/{order_id}/track", "anonymous": False,
         "owner": True, "sales": False, "partner": False, "admin": False},
        {"endpoint": "/api/kyc/*", "anonymous": False,
         "owner": True, "sales": False, "partner": False, "admin": False},
    ]
