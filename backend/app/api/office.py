"""Back-office router — lead queue, metrics, assignment, model retrain."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.db import get_session
from app.schemas.schemas import (
    LeadAssignReq,
    LeadAssignResp,
    LeadResp,
    MetricsResp,
    RetrainResp,
)
from app.security.auth import require_role
from app.services.services import MetricsService, ModelService

router = APIRouter(tags=["office"])


@router.get("/leads", response_model=list[LeadResp])
def leads(
    session: Session = Depends(get_session),
    _=Depends(require_role(["owner", "sales", "partner"])),
):
    service = MetricsService(session)
    return service.list_leads()


@router.get("/metrics", response_model=MetricsResp)
def metrics(
    session: Session = Depends(get_session),
    _=Depends(require_role(["owner", "sales", "partner"])),
):
    service = MetricsService(session)
    return service.get_metrics()


@router.post("/leads/{lead_id}/assign", response_model=LeadAssignResp)
def assign_lead(
    lead_id: str,
    req: LeadAssignReq,
    session: Session = Depends(get_session),
    _=Depends(require_role(["owner", "sales", "partner"])),
):
    service = MetricsService(session)
    result = service.assign_lead(lead_id, req.assignee, req.type)
    if not result:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadAssignResp(**result)


@router.post("/model/retrain", response_model=RetrainResp)
def retrain_model(
    session: Session | None = Depends(get_session),
    _=Depends(require_role(["owner"])),
):
    if session is None:
        from app.core.db import engine as _engine
        session = Session(_engine)
    service = ModelService(session)
    return service.retrain()


