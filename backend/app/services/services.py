"""Service layer — business logic / use-cases. Services call repositories, never routers."""
import uuid
from datetime import datetime, timedelta

from sqlmodel import Session

from app.core.config import get_settings
from app.models.models import (
    ConsentLedger,
    Lead,
    Order,
    Product,
    User,
)
from app.repositories import (
    ConsentLedgerRepository,
    GstinRegistryRepository,
    LeadRepository,
    NotificationLogRepository,
    OrderRepository,
    ProductRepository,
    UdyamRegistryRepository,
    UserRepository,
)
from app.rules.engine import RulesEngine
from app.security.auth import hash_password, verify_password
from app.services.notifications import notify_user_step
from app.services.ocr import (
    mask_gstin,
    validate_gstin_checksum,
    validate_udyam_format,
)

settings = get_settings()


# ---------------------------------------------------------------------------
# Auth Service
# ---------------------------------------------------------------------------
class AuthService:
    def __init__(self, session: Session):
        self.session = session
        self.users = UserRepository(session)

    def signup(self, email: str, phone: str, business_name: str, password: str) -> User:
        clean_email = email.strip().lower()
        if self.users.get_by_email(clean_email):
            raise ValueError("An account with this email already exists")
        user = User(
            user_id=f"USR-{uuid.uuid4().hex[:8].upper()}",
            email=clean_email,
            phone=phone.strip(),
            business_name=business_name.strip(),
            password_hash=hash_password(password),
            role="owner",
        )
        return self.users.create(user)

    def signin(self, email: str, password: str) -> User:
        clean_email = email.strip().lower()
        user = self.users.get_by_email(clean_email)
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")
        return user


# ---------------------------------------------------------------------------
# Catalogue Service
# ---------------------------------------------------------------------------
class CatalogueService:
    def __init__(self, session: Session):
        self.session = session
        self.products = ProductRepository(session)

    def list_products(self) -> list[Product]:
        return self.products.list_all()

    def seed(self, products: list[Product]) -> None:
        self.products.seed_if_empty(products)


# ---------------------------------------------------------------------------
# Advisor Service
# ---------------------------------------------------------------------------
class AdvisorService:
    def __init__(self, session: Session):
        self.session = session
        self.engine = RulesEngine(session)

    def recommend(self, profile: dict) -> dict:
        rec = self.engine.recommend_bundle(profile)
        pricing = self.engine.price_bundle(rec["bundle"])
        return {"recommendation": rec, "pricing": pricing}

    def quote(self, bundle: list[str], contract_months: int = 24) -> dict:
        return self.engine.price_bundle(bundle, contract_months)


# ---------------------------------------------------------------------------
# KYC Service
# ---------------------------------------------------------------------------
class KYCService:
    def __init__(self, session: Session):
        self.session = session
        self.consents = ConsentLedgerRepository(session)
        self.gstin_registry = GstinRegistryRepository(session)
        self.udyam_registry = UdyamRegistryRepository(session)

    def record_consent(
        self, order_id: str, consent_given: bool,
        marketing_consent: bool, language: str,
    ) -> ConsentLedger:
        ledger = ConsentLedger(
            order_id=order_id,
            purpose="kyc_verification",
            consent_given=consent_given,
            marketing_consent=marketing_consent,
            language=language,
            consent_hash=str(uuid.uuid4()),
        )
        return self.consents.create(ledger)

    def lookup_gstin(self, gstin: str) -> dict:
        gstin_clean = gstin.strip().upper()
        if len(gstin_clean) != 15:
            return {"error": "Invalid GSTIN format (must be 15 characters)", "status": "format_error"}
        if not validate_gstin_checksum(gstin_clean):
            return {"error": "Invalid GSTIN checksum", "status": "checksum_error"}

        record = self.gstin_registry.get_by_gstin(gstin_clean)
        if record:
            return {
                "gstin": record.gstin,
                "legal_name": record.legal_name,
                "trade_name": record.trade_name,
                "constitution": record.constitution,
                "state": record.state,
                "status": record.status,
                "gstin_masked": mask_gstin(record.gstin),
            }
        return {"error": "GSTIN not found in registry", "status": "not_found"}

    def lookup_udyam(self, number: str) -> dict:
        num_clean = number.strip().upper()
        if not validate_udyam_format(num_clean):
            return {
                "error": "Invalid Udyam number format (expected UDYAM-XX-00-NNNNNNN)",
                "status": "format_error",
            }

        record = self.udyam_registry.get_by_udyam(num_clean)
        if record:
            return {
                "udyam_number": record.udyam_number,
                "name": record.name,
                "status": record.status,
            }
        return {"error": "Udyam number not found in registry", "status": "not_found"}

    def validate(self, data: dict) -> dict:
        checks = []
        gstin = (data.get("gstin") or "").strip().upper()
        udyam = (data.get("udyam") or "").strip().upper()
        registry_status = data.get("registry_status", "Active")
        address_proof_date = data.get("address_proof_date", "")
        name_on_gstin = (data.get("name_on_gstin") or "").strip()
        name_on_udyam = (data.get("name_on_udyam") or "").strip()
        name_on_id = (data.get("name_on_id") or "").strip()

        # 1. GSTIN format + checksum
        if gstin:
            fmt_ok = len(gstin) == 15
            chk_ok = validate_gstin_checksum(gstin) if fmt_ok else False
            checks.append({
                "item": "GSTIN format & checksum",
                "status": "Pass" if (fmt_ok and chk_ok) else "Failed",
                "fix": "" if (fmt_ok and chk_ok) else "Enter a valid 15-character GSTIN",
            })
        else:
            checks.append({
                "item": "GSTIN format & checksum",
                "status": "Needs attention",
                "fix": "GSTIN not provided",
            })

        # 2. Registry status
        if registry_status == "Active":
            checks.append({"item": "Registry status", "status": "Pass", "fix": ""})
        elif registry_status in ("Cancelled", "Suspended"):
            checks.append({
                "item": "Registry status",
                "status": "Failed",
                "fix": f"GSTIN is {registry_status}. Please contact your CA or visit GST portal to resolve.",
            })
        else:
            checks.append({
                "item": "Registry status",
                "status": "Needs attention",
                "fix": "Could not verify registry status",
            })

        # 3. Udyam format
        if udyam:
            udyam_ok = validate_udyam_format(udyam)
            checks.append({
                "item": "Udyam number format",
                "status": "Pass" if udyam_ok else "Failed",
                "fix": "" if udyam_ok else "Format must be UDYAM-XX-00-NNNNNNN",
            })
        else:
            checks.append({
                "item": "Udyam number format",
                "status": "Needs attention",
                "fix": "Udyam number not provided",
            })

        # 4. Address proof age ≤ 90 days from DEMO_TODAY
        demo_today = datetime.strptime(settings.demo_today, "%Y-%m-%d")
        if address_proof_date:
            try:
                proof_date = datetime.strptime(address_proof_date, "%Y-%m-%d")
                age_days = (demo_today - proof_date).days
                if 0 <= age_days <= 90:
                    checks.append({"item": "Address proof age ≤ 90 days", "status": "Pass", "fix": ""})
                else:
                    cutoff = demo_today - timedelta(days=90)
                    checks.append({
                        "item": "Address proof age ≤ 90 days",
                        "status": "Failed",
                        "fix": f"Address proof is {age_days} days old. Upload a document dated after {cutoff.strftime('%d %b %Y')}.",
                    })
            except ValueError:
                checks.append({
                    "item": "Address proof age ≤ 90 days",
                    "status": "Needs attention",
                    "fix": "Could not parse date from document",
                })
        else:
            checks.append({
                "item": "Address proof age ≤ 90 days",
                "status": "Needs attention",
                "fix": "Address proof date not extracted",
            })

        # 5. Name consistency
        names = [n for n in [name_on_gstin, name_on_udyam, name_on_id] if n]
        if len(names) >= 2:
            def tokens(n: str) -> set:
                return set(n.lower().split())
            base = tokens(names[0])
            all_match = all(len(base & tokens(n)) >= 1 for n in names[1:])
            checks.append({
                "item": "Name consistency across documents",
                "status": "Pass" if all_match else "Needs attention",
                "fix": "" if all_match else "Business or owner name differs across documents.",
            })
        else:
            checks.append({
                "item": "Name consistency across documents",
                "status": "Needs attention",
                "fix": "Not enough documents to compare names",
            })

        statuses = [c["status"] for c in checks]
        overall = (
            "Failed" if "Failed" in statuses
            else "Needs attention" if "Needs attention" in statuses
            else "Pass"
        )
        return {"checks": checks, "overall": overall}

    def esign_otp(self) -> dict:
        return {"status": "sent", "demo_otp": "123456", "note": "Simulated for demo — use OTP 123456"}

    def esign_verify(self, otp: str) -> dict:
        if str(otp).strip() == "123456":
            return {"status": "verified", "signed_at": datetime.utcnow()}
        return {"status": "failed", "error": "Invalid OTP"}


# ---------------------------------------------------------------------------
# Order Service
# ---------------------------------------------------------------------------
class OrderService:
    def __init__(self, session: Session):
        self.session = session
        self.orders = OrderRepository(session)
        self.notifications = NotificationLogRepository(session)

    def create(self, data: dict) -> Order:
        order = Order(
            order_id=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            business_name=data.get("business_name", "Valued Customer"),
            phone=data.get("phone", "9876543210"),
            bundle_json=str(data.get("bundle", {})),
            monthly_total=float(data.get("monthly_total", 0)),
            one_time_total=float(data.get("one_time_total", 0)),
            language=data.get("language", "hi"),
            status="KYC verified",
        )
        created = self.orders.create(order)

        notify_user_step(
            event_type="kyc_verified",
            user_email="customer@example.com",
            user_phone=order.phone,
            order_id=order.order_id,
            details={"business_name": order.business_name, "monthly_total": order.monthly_total},
        )
        return created

    def track(self, order_id: str) -> dict:
        order = self.orders.get_by_id(order_id)
        if not order:
            raise ValueError("Order not found")

        statuses = [
            "Order placed", "KYC verified", "Installation scheduled", "Installed", "Activated",
        ]
        etas = ["Done", "30 min", "1-2 days", "2-3 days", "3-5 days"]
        messages = [
            "Your order has been received and logged.",
            "KYC documents and registry data verified successfully.",
            "Technician assigned, installation scheduled.",
            "Equipment and CPE installed, line testing in progress.",
            "Your service is live and fully activated!",
        ]
        current_idx = statuses.index(order.status) if order.status in statuses else 0

        timeline = []
        for i, (s, eta, msg) in enumerate(zip(statuses, etas, messages, strict=True)):
            timeline.append({
                "status": s,
                "done": i <= current_idx,
                "eta": "Done" if i <= current_idx else eta,
                "message": msg,
            })

        db_notifications = self.notifications.list_for_order(order_id)
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
                {"channel": "whatsapp", "text": f"✅ Order received ({order.order_id}). KYC verified.", "time": "Just now", "recipient": order.phone},
                {"channel": "sms", "text": f"Accel Business: Order {order.order_id} confirmed. Engineer being assigned.", "time": "Just now", "recipient": order.phone},
            ]

        return {
            "order": order,
            "timeline": timeline,
            "notifications": notifications,
            "comparison": "Estimated: ≤ 5 days vs typical 17.6 days baseline",
        }

    def reschedule(self, order_id: str, slot: str) -> dict:
        order = self.orders.get_by_id(order_id)
        if not order:
            raise ValueError("Order not found")
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

    def advance_time(self, order_id: str) -> dict:
        order = self.orders.get_by_id(order_id)
        if not order:
            return {"status": "ok", "new_status": "unknown", "message": "Order not found"}

        statuses = [
            "Order placed", "KYC verified", "Installation scheduled", "Installed", "Activated",
        ]
        if order.status in statuses:
            idx = statuses.index(order.status)
            if idx < len(statuses) - 1:
                order.status = statuses[idx + 1]
                self.session.add(order)
                self.session.commit()
                phone = order.phone or "9876543210"
                if order.status == "Installation scheduled":
                    notify_user_step(
                        "installation_scheduled", "customer@example.com", phone,
                        order_id, {"business_name": order.business_name},
                    )
                elif order.status == "Activated":
                    notify_user_step(
                        "activated", "customer@example.com", phone,
                        order_id, {"business_name": order.business_name},
                    )
        return {
            "status": "ok",
            "new_status": order.status,
            "message": "Simulated time advanced and real-time alerts sent",
        }


# ---------------------------------------------------------------------------
# Back-office / Metrics Service
# ---------------------------------------------------------------------------
class MetricsService:
    def __init__(self, session: Session):
        self.session = session
        self.leads = LeadRepository(session)

    def get_metrics(self) -> dict:
        return {
            "baseline": {
                "lead_to_activation": 7.4,
                "time_to_activate_days": 17.6,
                "acq_cost_per_activation": 15000,
                "status_chase_calls": 3,
                "churn_6m": 15.0,
            },
            "target": {
                "lead_to_activation": 12.0,
                "time_to_activate_days": 5.0,
                "acq_cost_per_activation": 8000,
                "status_chase_calls": 1,
                "churn_6m": 12.0,
            },
            "funnel": [
                {"stage": "Lead", "count": 5000},
                {"stage": "Contacted", "count": 3406},
                {"stage": "Needs assessed", "count": 1974},
                {"stage": "Quote accepted", "count": 861},
                {"stage": "KYC complete", "count": 588},
                {"stage": "Activated", "count": 368},
            ],
            "by_segment": [
                {"segment": "Micro retail & services", "share": 54, "activation": 4.1, "avg_bundle": 2505, "churn_6m": 22.7},
                {"segment": "Professional offices", "share": 25, "activation": 11.1, "avg_bundle": 6796, "churn_6m": 13.8},
                {"segment": "Small multi-site businesses", "share": 10, "activation": 11.0, "avg_bundle": 31233, "churn_6m": 10.8},
                {"segment": "Small manufacturers", "share": 11, "activation": 12.8, "avg_bundle": 19980, "churn_6m": 8.1},
            ],
            "by_source": [
                {"source": "Referral", "cac": 4100, "conversion": 14.8},
                {"source": "WhatsApp campaign", "cac": 4000, "conversion": 2.8},
                {"source": "Inbound call", "cac": 5100, "conversion": 8.2},
                {"source": "Website", "cac": 6400, "conversion": 5.1},
                {"source": "Channel partner", "cac": 20900, "conversion": 3.2},
                {"source": "Field sales", "cac": 24300, "conversion": 6.1},
            ],
        }

    def list_leads(self) -> list[dict]:
        all_leads = self.leads.list_all()
        result = []
        for lead in all_leads:
            score, reasons = self._score_lead(lead)
            result.append({
                "lead_id": lead.lead_id,
                "business_name": lead.business_name,
                "business_type": lead.business_type,
                "segment": lead.segment,
                "city": lead.city,
                "language": lead.preferred_language,
                "bundle_drafted": self._bundle_name(lead.segment),
                "propensity_score": score,
                "reasons": reasons,
                "ai_summary": f"{lead.business_name} in {lead.city} — {lead.segment}. Drop reason: {lead.drop_reason or 'N/A'}.",
                "suggested_action": self._suggest_action(lead),
                "stage": lead.stage_reached,
                "drop_reason": lead.drop_reason,
                "has_gstin": lead.has_gstin,
            })
        result.sort(key=lambda x: x["propensity_score"], reverse=True)
        return result[:50]

    def assign_lead(self, lead_id: str, assignee: str, assignee_type: str) -> dict | None:
        # Persist assignment — extend Lead model later; for now return confirmation
        lead = self.leads.get_by_id(lead_id)
        if not lead:
            return None
        return {
            "status": "assigned",
            "lead_id": lead_id,
            "assignee": assignee,
            "assignee_type": assignee_type,
            "attribution": "partner-assisted digital",
            "message": "Lead assigned. Commission attribution recorded.",
        }

    def _score_lead(self, lead: Lead) -> tuple[int, list[str]]:
        score = 30
        if lead.has_gstin == "Y":
            score += 20
        if lead.segment == "Professional offices":
            score += 15
        elif lead.segment == "Small manufacturers":
            score += 10
        if lead.has_udyam == "Y":
            score += 10
        if lead.city_tier == 1:
            score += 10
        elif lead.city_tier == 2:
            score += 5
        if lead.lead_source in ("Referral", "WhatsApp campaign"):
            score += 10
        if lead.employee_count and lead.employee_count >= 5:
            score += 5
        reasons = self._top_reasons(lead)
        return max(5, min(99, score)), reasons

    def _top_reasons(self, lead: Lead) -> list[str]:
        reasons = []
        if lead.has_gstin == "Y":
            reasons.append("GSTIN present — eligible for full bundle")
        elif lead.has_gstin == "N":
            reasons.append("No GSTIN — eligible for Starter bundle")
        if lead.segment == "Professional offices":
            reasons.append("High-value Professional segment (11% conversion)")
        elif lead.segment == "Small multi-site businesses":
            reasons.append("Multi-site — high bundle value potential")
        elif lead.segment == "Small manufacturers":
            reasons.append("Manufacturer segment — good activation rate (12.8%)")
        if lead.city_tier == 1:
            reasons.append("Tier 1 city — full product catalogue eligible")
        if lead.lead_source == "Referral":
            reasons.append("Referral lead — 14.8% conversion historically")
        if not reasons:
            reasons.append("Digital-first lead — lower acquisition cost")
        return reasons[:3]

    def _suggest_action(self, lead: Lead) -> str:
        dr = (lead.drop_reason or "").lower()
        lang = lead.preferred_language or "English"
        if "unreachable" in dr or "wrong number" in dr:
            return f"Try WhatsApp in {lang} — provide digital self-serve link"
        if "price" in dr:
            return f"Share Starter tier quote in {lang} — emphasise bundle saving"
        if "time" in dr or "visit" in dr:
            return "Send self-serve onboarding link — no visit needed"
        if "complex" in dr or "slow" in dr:
            return "Walk through quote over a 10-minute call with screen share"
        if "mobile" in dr:
            return "Lead with P07/P08 mobile plan + one honest upsell"
        if "gstin" in dr or "gst" in dr:
            return "Explain GST-free Starter bundle — help get GSTIN if interested"
        return f"Call in {lang} with quote ready — high propensity lead"

    def _bundle_name(self, segment: str) -> str:
        names = {
            "Micro retail & services": "Dukaan Digital",
            "Professional offices": "Clinic/Office Pro",
            "Small multi-site businesses": "One Bill",
            "Small manufacturers": "Plant Connect",
        }
        return names.get(segment, "Accel Business Bundle")


# ---------------------------------------------------------------------------
# Model Retrain (placeholder — full implementation in U5)
# ---------------------------------------------------------------------------
class ModelService:
    def __init__(self, session: Session):
        self.session = session

    def retrain(self) -> dict:
        return {
            "status": "retrained",
            "auc": 0.0,
            "samples": 0,
            "features": [],
            "excluded_features": ["preferred_language", "state", "stage_reached", "drop_reason", "outcome"],
            "note": "Model retraining stub — full implementation in U5",
        }
