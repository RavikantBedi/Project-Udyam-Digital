"""Pydantic request/response schemas for all API endpoints."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------
class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    request_id: str | None = None
    status_code: int


class Message(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class SignupReq(BaseModel):
    email: EmailStr
    phone: str = Field(min_length=8, max_length=20)
    business_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class SigninReq(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    user_id: str
    email: str
    phone: str
    business_name: str
    role: str
    email_verified: bool = False
    phone_verified: bool = False
    is_active: bool = True
    created_at: datetime


# ---------------------------------------------------------------------------
# Advisor
# ---------------------------------------------------------------------------
class MessageReq(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[dict] = []
    profile: dict = {}


class MessageResp(BaseModel):
    reply: str
    profile: dict
    recommendation: dict | None = None
    pricing: dict | None = None
    quick_replies: list[str] = []
    all_slots_filled: bool = False
    mode: str
    action: str | None = None


class BundleRecommendReq(BaseModel):
    profile: dict = {}


# ---------------------------------------------------------------------------
# Quote / Bundle
# ---------------------------------------------------------------------------
class BundleItemResp(BaseModel):
    product_id: str
    name: str
    category: str
    monthly: float
    setup: float
    install_days: int
    min_contract_months: int


class BundlePricingResp(BaseModel):
    items: list[BundleItemResp]
    monthly_total: float
    one_time_total: float
    gst: float
    first_bill_estimate: float
    bundle_saving: float
    max_install_days: int
    contract_months: int


class BundleRecommendResp(BaseModel):
    recommendation: dict
    pricing: BundlePricingResp


class QuoteReq(BaseModel):
    bundle: list[str] = []
    contract_months: int = Field(24, ge=1, le=60)


# ---------------------------------------------------------------------------
# KYC
# ---------------------------------------------------------------------------
class ConsentReq(BaseModel):
    order_id: str
    consent_given: bool
    marketing_consent: bool = False
    language: str = "hi"


class ConsentResp(BaseModel):
    status: str
    consent_hash: str


class KYCCheckResp(BaseModel):
    item: str
    status: str  # Pass | Needs attention | Failed
    fix: str = ""


class KYCValidateReq(BaseModel):
    gstin: str | None = None
    udyam: str | None = None
    registry_status: str | None = "Active"
    address_proof_date: str | None = None
    name_on_gstin: str | None = None
    name_on_udyam: str | None = None
    name_on_id: str | None = None


class KYCValidateResp(BaseModel):
    checks: list[KYCCheckResp]
    overall: str


class GSTINLookupResp(BaseModel):
    gstin: str
    legal_name: str | None = None
    trade_name: str | None = None
    constitution: str | None = None
    state: str | None = None
    status: str | None = None
    gstin_masked: str | None = None


class UdyamLookupResp(BaseModel):
    udyam_number: str
    name: str | None = None
    status: str | None = None


class KYCUploadResp(BaseModel):
    filename: str
    status: str
    size: int


class ESIGNOTPResp(BaseModel):
    status: str
    demo_otp: str
    note: str


class ESIGNVerifyResp(BaseModel):
    status: str
    signed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Orders / Tracker
# ---------------------------------------------------------------------------
class OrderCreateReq(BaseModel):
    business_name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=8, max_length=20)
    language: str = "hi"
    bundle: list[str] = []
    monthly_total: float = 0
    one_time_total: float = 0


class OrderResp(BaseModel):
    order_id: str
    business_name: str
    phone: str
    status: str
    bundle_json: str
    monthly_total: float
    one_time_total: float
    language: str
    created_at: datetime


class TimelineItem(BaseModel):
    status: str
    done: bool
    eta: str
    message: str


class NotificationItem(BaseModel):
    channel: str
    text: str
    time: str
    recipient: str


class TrackResp(BaseModel):
    order: OrderResp
    timeline: list[TimelineItem]
    notifications: list[NotificationItem]
    comparison: str


class RescheduleReq(BaseModel):
    slot: str = "Tomorrow 2:00 PM"


class RescheduleResp(BaseModel):
    status: str
    order_id: str
    new_slot: str
    notifications_sent: list[str]


class AdvanceTimeResp(BaseModel):
    status: str
    new_status: str
    message: str


# ---------------------------------------------------------------------------
# Office / Back-office
# ---------------------------------------------------------------------------
class LeadResp(BaseModel):
    lead_id: str
    business_name: str
    business_type: str
    segment: str
    city: str
    language: str
    bundle_drafted: str
    propensity_score: int
    reasons: list[str]
    ai_summary: str
    suggested_action: str
    stage: str
    drop_reason: str | None = None
    has_gstin: str


class MetricsBaseline(BaseModel):
    lead_to_activation: float
    time_to_activate_days: float
    acq_cost_per_activation: float
    status_chase_calls: float
    churn_6m: float


class MetricsTarget(BaseModel):
    lead_to_activation: float
    time_to_activate_days: float
    acq_cost_per_activation: float
    status_chase_calls: float
    churn_6m: float


class FunnelStage(BaseModel):
    stage: str
    count: int


class SegmentData(BaseModel):
    segment: str
    share: int
    activation: float
    avg_bundle: float
    churn_6m: float


class SourceData(BaseModel):
    source: str
    cac: int
    conversion: float


class MetricsResp(BaseModel):
    baseline: MetricsBaseline
    target: MetricsTarget
    funnel: list[FunnelStage]
    by_segment: list[SegmentData]
    by_source: list[SourceData]


class LeadAssignReq(BaseModel):
    assignee: str
    type: str = "field"


class LeadAssignResp(BaseModel):
    status: str
    lead_id: str
    assignee: str
    assignee_type: str
    attribution: str
    message: str


class RetrainResp(BaseModel):
    status: str
    auc: float
    samples: int
    features: list[str]
    excluded_features: list[str]
    note: str


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------
class ProductResp(BaseModel):
    id: int | None = None
    product_id: str
    name: str
    category: str
    price_min: float
    price_max: float
    one_time_setup: float
    min_contract_months: int
    available_city_tiers: str
    min_employees: int
    min_sites: int
    requires_gstin: str
    requires_one_of: str
    typical_install_days: int
    target_segments: str


class HealthResp(BaseModel):
    status: str
    database: str
    version: str = "1.0.0"


# Fix forward references
TokenResponse.model_rebuild()


# ---------------------------------------------------------------------------
# Auth (extended)
# ---------------------------------------------------------------------------
class RefreshReq(BaseModel):
    refresh_token: str


class SignoutReq(BaseModel):
    refresh_token: str | None = None


class ChangePasswordReq(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=128)


class ForgotPasswordReq(BaseModel):
    email: EmailStr


class ResetPasswordReq(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=10, max_length=128)


class OtpVerifyReq(BaseModel):
    target: str = Field(min_length=8, max_length=50)
    code: str = Field(min_length=6, max_length=6)
    purpose: str = Field(pattern="^(signup|signin|reset_password)$")


class OtpSendReq(BaseModel):
    target: str = Field(min_length=8, max_length=50)
    purpose: str = Field(pattern="^(signup|signin|reset_password)$")
    channel: str = "sms"


class TokenResp(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserCreateReq(BaseModel):
    email: EmailStr
    phone: str = Field(min_length=8, max_length=20)
    business_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=10, max_length=128)
    role: str = Field(pattern="^(owner|sales|partner|admin)$")


class UserUpdateRoleReq(BaseModel):
    role: str = Field(pattern="^(owner|sales|partner|admin)$")


class LeadAssignmentCreateReq(BaseModel):
    lead_id: str
    assignee_type: str = Field(pattern="^(field|partner)$")
    assignee_id: str
    attribution_tag: str = "partner-assisted digital"
    outcome: str | None = None


class LeadAssignmentOutcomeReq(BaseModel):
    outcome: str


class LeadAssignmentResp(BaseModel):
    id: int
    lead_id: str
    assignee_type: str
    assignee_id: str
    assigned_by: str
    attribution_tag: str
    outcome: str | None
    created_at: datetime
    updated_at: datetime


class AuditLogResp(BaseModel):
    id: int
    actor_id: str | None
    actor_role: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    ip_address: str | None
    before_hash: str | None
    after_hash: str | None
    created_at: datetime


class RoleMatrixResp(BaseModel):
    endpoint: str
    anonymous: bool
    owner: bool
    sales: bool
    partner: bool
    admin: bool


# Fix forward references
TokenResp.model_rebuild()

