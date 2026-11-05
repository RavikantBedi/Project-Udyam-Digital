import hashlib
import uuid
from datetime import datetime, timedelta
import jwt
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlmodel import Session, select
from app.core.db import get_session
from app.core.config import get_settings
from app.models.models import User, NotificationLog
from app.services.notifications import notify_user_step

router = APIRouter()
settings = get_settings()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


class SignupReq(BaseModel):
    email: str
    phone: str
    business_name: str
    password: str


class SigninReq(BaseModel):
    email: str
    password: str


@router.post("/auth/signup")
def signup(req: SignupReq, session: Session = Depends(get_session)):
    clean_email = req.email.strip().lower()
    clean_phone = req.phone.strip()

    # Check existing user
    existing = session.exec(select(User).where(User.email == clean_email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    user = User(
        user_id=f"USR-{uuid.uuid4().hex[:8].upper()}",
        email=clean_email,
        phone=clean_phone,
        business_name=req.business_name.strip(),
        password_hash=hash_password(req.password),
        role="owner",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # Trigger real-time Email, SMS and WhatsApp welcome
    notify_user_step(
        event_type="signup",
        user_email=user.email,
        user_phone=user.phone,
        details={"business_name": user.business_name},
    )

    token = create_token(user.user_id, user.email, user.role)
    return {
        "status": "success",
        "token": token,
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "phone": user.phone,
            "business_name": user.business_name,
            "role": user.role,
        },
        "notifications_dispatched": ["email", "sms", "whatsapp"],
    }


@router.post("/auth/signin")
def signin(req: SigninReq, session: Session = Depends(get_session)):
    clean_email = req.email.strip().lower()
    hashed = hash_password(req.password)

    user = session.exec(
        select(User).where(User.email == clean_email, User.password_hash == hashed)
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Send real-time Email & SMS & WhatsApp alert on sign-in
    notify_user_step(
        event_type="signin",
        user_email=user.email,
        user_phone=user.phone,
        details={"business_name": user.business_name},
    )

    token = create_token(user.user_id, user.email, user.role)
    return {
        "status": "success",
        "token": token,
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "phone": user.phone,
            "business_name": user.business_name,
            "role": user.role,
        },
        "notifications_dispatched": ["email", "sms", "whatsapp"],
    }


@router.get("/notifications/live")
def get_live_notifications(
    channel: str = None, limit: int = 30, session: Session = Depends(get_session)
):
    """Fetch live feed of real-time SMS, Email, and WhatsApp notifications dispatched across steps."""
    query = select(NotificationLog).order_by(NotificationLog.created_at.desc())
    if channel:
        query = query.where(NotificationLog.channel == channel)
    logs = session.exec(query.limit(limit)).all()
    return logs
