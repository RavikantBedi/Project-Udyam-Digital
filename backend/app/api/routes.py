"""Core routes router — catalogue, orders, tracker, demo controls."""

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.schemas.schemas import (
    AdvanceTimeResp,
    OrderCreateReq,
    OrderResp,
    ProductResp,
    RescheduleReq,
    RescheduleResp,
    TrackResp,
)
from app.services.services import CatalogueService, OrderService

router = APIRouter()


@router.get("/catalogue", response_model=list[ProductResp])
def catalogue(session: Session = Depends(get_session)):
    service = CatalogueService(session)
    products = service.list_products()
    return [
        ProductResp(
            id=p.id,
            product_id=p.product_id,
            name=p.name,
            category=p.category,
            price_min=p.price_min,
            price_max=p.price_max,
            one_time_setup=p.one_time_setup,
            min_contract_months=p.min_contract_months,
            available_city_tiers=p.available_city_tiers,
            min_employees=p.min_employees,
            min_sites=p.min_sites,
            requires_gstin=p.requires_gstin,
            requires_one_of=p.requires_one_of,
            typical_install_days=p.typical_install_days,
            target_segments=p.target_segments,
        )
        for p in products
    ]


@router.post("/orders", response_model=OrderResp, status_code=status.HTTP_201_CREATED)
def create_order(
    req: OrderCreateReq,
    session: Session = Depends(get_session),
):
    service = OrderService(session)
    order = service.create(req.model_dump())
    return OrderResp.model_validate(order)


@router.get("/orders/{order_id}/track", response_model=TrackResp)
def track_order(order_id: str, session: Session = Depends(get_session)):
    service = OrderService(session)
    result = service.track(order_id)
    return TrackResp(**result)


@router.post("/orders/{order_id}/reschedule", response_model=RescheduleResp)
def reschedule_order(
    order_id: str,
    req: RescheduleReq,
    session: Session = Depends(get_session),
):
    service = OrderService(session)
    result = service.reschedule(order_id, req.slot)
    return RescheduleResp(**result)


@router.post("/demo/advance-time", response_model=AdvanceTimeResp)
def advance_time(
    order_id: str = "ORD-DEMO0001",
    session: Session = Depends(get_session),
):
    service = OrderService(session)
    result = service.advance_time(order_id)
    return AdvanceTimeResp(**result)


# Fix forward reference import
