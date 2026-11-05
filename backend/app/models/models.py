from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: str = Field(index=True, unique=True)
    name: str
    category: str
    price_min: float
    price_max: float
    one_time_setup: float
    min_contract_months: int
    available_city_tiers: str
    min_employees: int = 0
    min_sites: int = 1
    requires_gstin: str = "N"
    requires_one_of: str = ""
    typical_install_days: int = 3
    target_segments: str = ""


class Lead(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    lead_id: str = Field(index=True, unique=True)
    business_name: str
    business_type: str
    segment: str
    city: str
    city_tier: int
    preferred_language: str
    employee_count: int
    num_sites: int
    has_gstin: str
    gstin: str = ""
    has_udyam: str
    udyam_number: str = ""
    stage_reached: str
    outcome: str = ""
    drop_reason: str = ""
    monthly_bundle_value_inr: float = 0
    lead_source: str = ""


class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: str = Field(index=True, unique=True)
    lead_id: str = ""
    business_name: str
    phone: str = ""
    status: str = "Order placed"
    bundle_json: str = ""
    monthly_total: float = 0
    one_time_total: float = 0
    language: str = "hi"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    installed_at: Optional[datetime] = None


class ConsentLedger(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: str
    purpose: str
    consent_given: bool
    marketing_consent: bool
    language: str
    version: str = "1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    consent_hash: str = ""


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    phone: str = Field(index=True)
    business_name: str = ""
    password_hash: str
    role: str = "owner"  # owner, sales, partner
    created_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    channel: str  # 'email', 'sms', 'whatsapp'
    recipient: str  # email address or phone number
    subject: str = ""
    message: str
    status: str = "sent"  # 'sent', 'delivered', 'failed'
    order_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
