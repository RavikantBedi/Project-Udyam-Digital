"""SQLModel database models — all tables for the Accel Business platform."""
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
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
    id: int | None = Field(default=None, primary_key=True)
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
    id: int | None = Field(default=None, primary_key=True)
    order_id: str = Field(index=True, unique=True)
    lead_id: str = ""
    business_name: str
    phone: str = ""
    status: str = "Order placed"
    bundle_json: str = ""
    monthly_total: float = 0
    one_time_total: float = 0
    language: str = "hi"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    installed_at: datetime | None = None


class ConsentLedger(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    order_id: str
    purpose: str
    consent_given: bool
    marketing_consent: bool
    language: str
    version: str = "1.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    consent_hash: str = ""


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    phone: str = Field(index=True)
    business_name: str = ""
    password_hash: str
    password_algorithm: str = "argon2id"  # argon2id | sha256 (legacy — rejected)
    role: str = "owner"  # owner, sales, partner, admin
    email_verified: bool = False
    phone_verified: bool = False
    is_active: bool = True
    failed_login_attempts: int = 0
    locked_until: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NotificationLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    channel: str  # 'email', 'sms', 'whatsapp'
    recipient: str  # email address or phone number
    subject: str = ""
    message: str
    status: str = "sent"  # 'sent', 'delivered', 'failed'
    order_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GstinRegistry(SQLModel, table=True):
    __tablename__ = "gstin_registry"
    id: int | None = Field(default=None, primary_key=True)
    gstin: str = Field(index=True, unique=True)
    legal_name: str | None = None
    trade_name: str | None = None
    constitution: str | None = None
    principal_place_of_business: str | None = None
    state: str | None = None
    registration_date: str | None = None
    status: str | None = None


class UdyamRegistry(SQLModel, table=True):
    __tablename__ = "udyam_registry"
    id: int | None = Field(default=None, primary_key=True)
    udyam_number: str = Field(index=True, unique=True)
    name: str | None = None
    status: str | None = None


class RefreshToken(SQLModel, table=True):
    """Rotating refresh tokens — token stored hashed."""
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    token_hash: str = Field(index=True, unique=True)
    expires_at: datetime
    revoked_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    device_info: str | None = None
    ip_address: str | None = None


class OtpCode(SQLModel, table=True):
    """One-time passwords for phone/email verification and password reset."""
    id: int | None = Field(default=None, primary_key=True)
    purpose: str  # 'signup', 'signin', 'reset_password'
    target: str  # email or phone number
    code_hash: str = Field(index=True)
    expires_at: datetime
    attempts: int = 0
    used_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LeadAssignment(SQLModel, table=True):
    """Persisted lead assignments with attribution — separate back-office data."""
    id: int | None = Field(default=None, primary_key=True)
    lead_id: str = Field(index=True)
    assignee_type: str  # 'field' | 'partner'
    assignee_id: str = Field(index=True)
    assigned_by: str  # user_id of assigner
    attribution_tag: str = "partner-assisted digital"
    outcome: str | None = None  # 'closed_won', 'closed_lost', 'contacted', etc.
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuditLog(SQLModel, table=True):
    """Immutable audit log — actor, role, action, resource, IP, timestamps."""
    id: int | None = Field(default=None, primary_key=True)
    actor_id: str | None = None
    actor_role: str | None = None
    action: str  # 'login', 'signup', 'kyc_view', 'document_download', 'export', 'assignment', 'settings_change'
    resource_type: str | None = None
    resource_id: str | None = None
    ip_address: str | None = None
    before_hash: str | None = None
    after_hash: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
