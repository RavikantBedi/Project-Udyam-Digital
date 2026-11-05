from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.db import get_session
from app.core.config import get_data_dir
from app.models.models import Product, Order, NotificationLog
from app.rules.engine import RulesEngine
from app.services.notifications import notify_user_step
import uuid
import csv
import os

router = APIRouter()


@router.get("/catalogue")
def catalogue(session: Session = Depends(get_session)):
    products = session.exec(select(Product)).all()
    return products


@router.post("/orders")
def create_order(data: dict, session: Session = Depends(get_session)):
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    phone = data.get("phone", "9876543210")
    bname = data.get("business_name", "Valued Customer")
    monthly = float(data.get("monthly_total", 4299))

    order = Order(
        order_id=order_id,
        business_name=bname,
        phone=phone,
        bundle_json=str(data.get("bundle", {})),
        monthly_total=monthly,
        one_time_total=float(data.get("one_time_total", 0)),
        language=data.get("language", "hi"),
        status="KYC verified",
    )
    session.add(order)
    session.commit()
    session.refresh(order)

    # Trigger real-time notifications across SMS and WhatsApp
    notify_user_step(
        event_type="kyc_verified",
        user_email="customer@example.com",
        user_phone=phone,
        order_id=order_id,
        details={"business_name": bname, "monthly_total": monthly},
    )

    return order


@router.get("/orders/{order_id}/track")
def track_order(order_id: str, session: Session = Depends(get_session)):
    order = session.exec(select(Order).where(Order.order_id == order_id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    statuses = [
        "Order placed",
        "KYC verified",
        "Installation scheduled",
        "Installed",
        "Activated",
    ]
    current_idx = statuses.index(order.status) if order.status in statuses else 0
    etas = ["Done", "30 min", "1-2 days", "2-3 days", "3-5 days"]
    messages = [
        "Your order has been received and logged.",
        "KYC documents and registry data verified successfully.",
        "Technician assigned, installation scheduled.",
        "Equipment and CPE installed, line testing in progress.",
        "Your service is live and fully activated!",
    ]

    timeline = []
    for i, (s, eta, msg) in enumerate(zip(statuses, etas, messages)):
        timeline.append({
            "status": s,
            "done": i <= current_idx,
            "eta": "Done" if i <= current_idx else eta,
            "message": msg,
        })

    # Retrieve real-time logged notifications for this order from NotificationLog
    db_notifications = session.exec(
        select(NotificationLog)
        .where(
            (NotificationLog.order_id == order_id)
            | (NotificationLog.channel.in_(["whatsapp", "sms"]))
        )
        .order_by(NotificationLog.created_at.desc())
        .limit(10)
    ).all()

    notifications = []
    for n in db_notifications:
        notifications.append({
            "channel": n.channel,
            "text": n.message,
            "time": n.created_at.strftime("%I:%M %p"),
            "recipient": n.recipient,
        })

    if not notifications:
        notifications = [
            {
                "channel": "whatsapp",
                "text": f"✅ Order received ({order.order_id}). KYC verified.",
                "time": "Just now",
            },
            {
                "channel": "sms",
                "text": f"Accel Business: Order {order.order_id} confirmed. Engineer being assigned.",
                "time": "Just now",
            },
        ]

    return {
        "order": {
            "order_id": order.order_id,
            "business_name": order.business_name,
            "status": order.status,
            "monthly_total": order.monthly_total,
            "one_time_total": order.one_time_total,
            "language": order.language,
            "created_at": str(order.created_at),
        },
        "timeline": timeline,
        "notifications": notifications,
        "comparison": "Estimated: ≤ 5 days vs typical 17.6 days baseline",
    }


@router.post("/orders/{order_id}/reschedule")
def reschedule_order(
    order_id: str, data: dict, session: Session = Depends(get_session)
):
    order = session.exec(select(Order).where(Order.order_id == order_id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    slot = data.get("slot", "Tomorrow 2:00 PM")

    notify_user_step(
        event_type="installation_scheduled",
        user_email="customer@example.com",
        user_phone=order.phone or "9876543210",
        order_id=order_id,
        details={"slot": slot},
    )

    return {
        "status": "rescheduled",
        "order_id": order_id,
        "new_slot": slot,
        "notifications_sent": ["whatsapp", "sms"],
    }


@router.post("/demo/advance-time")
def advance_time(data: dict = {}, session: Session = Depends(get_session)):
    """Advance a demo order's status to next stage and trigger live real-time WhatsApp & SMS."""
    order_id = data.get("order_id", "ORD-DEMO0001")
    order = session.exec(select(Order).where(Order.order_id == order_id)).first()
    statuses = [
        "Order placed",
        "KYC verified",
        "Installation scheduled",
        "Installed",
        "Activated",
    ]
    if order and order.status in statuses:
        idx = statuses.index(order.status)
        if idx < len(statuses) - 1:
            order.status = statuses[idx + 1]
            session.add(order)
            session.commit()

            # Trigger real-time notifications for this stage
            phone = order.phone or "9876543210"
            if order.status == "Installation scheduled":
                notify_user_step(
                    "installation_scheduled",
                    "customer@example.com",
                    phone,
                    order_id,
                    {"business_name": order.business_name},
                )
            elif order.status == "Activated":
                notify_user_step(
                    "activated",
                    "customer@example.com",
                    phone,
                    order_id,
                    {"business_name": order.business_name},
                )

    return {
        "status": "ok",
        "new_status": order.status if order else "unknown",
        "message": "Simulated time advanced and real-time alerts sent",
    }


@router.post("/bundle/recommend")
def bundle_recommend(data: dict, session: Session = Depends(get_session)):
    engine = RulesEngine(session)
    rec = engine.recommend_bundle(data)
    pricing = engine.price_bundle(rec["bundle"])
    return {"recommendation": rec, "pricing": pricing}


@router.post("/quote")
def quote(data: dict, session: Session = Depends(get_session)):
    engine = RulesEngine(session)
    pricing = engine.price_bundle(
        data.get("bundle", []),
        contract_months=data.get("contract_months", 24),
    )
    return pricing


@router.get("/lookup/gstin/{gstin}")
def lookup_gstin_route(gstin: str):
    path = os.path.join(get_data_dir(), "mock_gstin_registry.csv")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["gstin"].strip().upper() == gstin.strip().upper():
                    return row
    return {"error": "not found"}


@router.get("/lookup/udyam/{number}")
def lookup_udyam_route(number: str):
    path = os.path.join(get_data_dir(), "mock_udyam_registry.csv")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["udyam_number"].strip().upper() == number.strip().upper():
                    return row
    return {"error": "not found"}
