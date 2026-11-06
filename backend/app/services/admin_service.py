"""Admin service — back-office operations with RBAC and audit."""
import hashlib
import secrets as _secrets
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.models import (
    AuditLog,
    Lead,
    LeadAssignment,
    User,
)
from app.repositories import (
    AuditLogRepository,
    LeadAssignmentRepository,
    LeadRepository,
    NotificationLogRepository,
    UserRepository,
)
from app.security.auth import hash_password

settings = get_settings()


class AdminService:
    def __init__(self, session: Session):
        self.session = session
        self.users = UserRepository(session)
        self.leads = LeadRepository(session)
        self.assignments = LeadAssignmentRepository(session)
        self.audit = AuditLogRepository(session)
        self.notifications = NotificationLogRepository(session)

    # ---- audit helpers ----
    def _audit(
        self,
        actor_user_id: str | None,
        actor_role: str | None,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        before_hash: str | None = None,
        after_hash: str | None = None,
    ) -> None:
        self.audit.create(
            actor_id=actor_user_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            before_hash=before_hash,
            after_hash=after_hash,
        )

    # ---- users ----
    def list_users(self, actor_user_id: str | None, actor_role: str | None) -> list[User]:
        if actor_role != "admin":
            raise PermissionError("Only admin can list users")
        self._audit(actor_user_id, actor_role, "user_list", resource_type="user")
        return self.users.list_all()

    def create_user(
        self,
        actor_user_id: str | None,
        actor_role: str | None,
        email: str,
        phone: str,
        business_name: str,
        password: str,
        role: str,
        ip_address: str | None = None,
    ) -> User:
        if actor_role != "admin":
            raise PermissionError("Only admin can create users")
        clean_email = email.strip().lower()
        if self.users.get_by_email(clean_email):
            raise ValueError("An account with this email already exists")
        user = User(
            user_id=f"USR-{_secrets.token_hex(4).upper()}",
            email=clean_email,
            phone=phone.strip(),
            business_name=business_name.strip(),
            password_hash=hash_password(password),
            password_algorithm="argon2id",
            role=role,
        )
        created = self.users.create(user)
        self._audit(
            actor_user_id,
            actor_role,
            "user_create",
            resource_type="user",
            resource_id=created.user_id,
            ip_address=ip_address,
            after_hash=hashlib.sha256(clean_email.encode()).hexdigest()[:16],
        )
        return created

    def update_user_role(
        self,
        actor_user_id: str | None,
        actor_role: str | None,
        user_id: str,
        new_role: str,
        ip_address: str | None = None,
    ) -> User:
        if actor_role != "admin":
            raise PermissionError("Only admin can update user roles")
        user = self.users.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        before = user.role
        user.role = new_role
        self.users.save(user)
        self._audit(
            actor_user_id,
            actor_role,
            "user_role_change",
            resource_type="user",
            resource_id=user_id,
            ip_address=ip_address,
            before_hash=before,
            after_hash=new_role,
        )
        return user

    # ---- leads ----
    def list_leads(
        self,
        actor_user_id: str | None,
        actor_role: str | None,
    ) -> list[Lead]:
        """Role-scoped lead list."""
        all_leads = self.leads.list_all()
        if actor_role == "admin":
            self._audit(actor_user_id, actor_role, "lead_list_all", resource_type="lead")
            return all_leads
        if actor_role == "sales":
            self._audit(actor_user_id, actor_role, "lead_list_sales", resource_type="lead")
            return all_leads
        if actor_role == "partner":
            assignments = self.assignments.list_for_assignee(actor_user_id or "")
            assigned_lead_ids = {a.lead_id for a in assignments}
            result = [lead for lead in all_leads if lead.lead_id in assigned_lead_ids]
            self._audit(actor_user_id, actor_role, "lead_list_partner", resource_type="lead")
            return result
        self._audit(actor_user_id, actor_role, "lead_list_owner_empty", resource_type="lead")
        return []

    def assign_lead(
        self,
        actor_user_id: str | None,
        actor_role: str | None,
        lead_id: str,
        assignee_type: str,
        assignee_id: str,
        attribution_tag: str,
        outcome: str | None = None,
        ip_address: str | None = None,
    ) -> LeadAssignment:
        if actor_role not in ("admin", "sales"):
            raise PermissionError("Only admin or sales can assign leads")
        lead = self.session.exec(select(Lead).where(Lead.lead_id == lead_id)).first()
        if not lead:
            raise ValueError("Lead not found")
        assignment = LeadAssignment(
            lead_id=lead_id,
            assignee_type=assignee_type,
            assignee_id=assignee_id,
            assigned_by=actor_user_id or "",
            attribution_tag=attribution_tag or "partner-assisted digital",
            outcome=outcome,
        )
        self.session.add(assignment)
        self.session.commit()
        self.session.refresh(assignment)
        self._audit(
            actor_user_id,
            actor_role,
            "lead_assign",
            resource_type="lead",
            resource_id=lead_id,
            ip_address=ip_address,
            after_hash=f"{assignee_type}:{assignee_id}",
        )
        return assignment

    def update_assignment_outcome(
        self,
        actor_user_id: str | None,
        actor_role: str | None,
        assignment_id: int,
        outcome: str,
        ip_address: str | None = None,
    ) -> LeadAssignment:
        if actor_role not in ("admin", "sales", "partner"):
            raise PermissionError("Insufficient permissions")
        la = self.session.exec(
            select(LeadAssignment).where(LeadAssignment.id == assignment_id)
        ).first()
        if not la:
            raise ValueError("Assignment not found")
        if actor_role == "partner" and la.assignee_id != (actor_user_id or ""):
            raise PermissionError("Cannot update another partner's assignment")
        before = la.outcome
        la.outcome = outcome
        la.updated_at = datetime.now(UTC)
        self.session.add(la)
        self.session.commit()
        self.session.refresh(la)
        self._audit(
            actor_user_id,
            actor_role,
            "lead_assignment_outcome",
            resource_type="lead_assignment",
            resource_id=str(assignment_id),
            ip_address=ip_address,
            before_hash=before,
            after_hash=outcome,
        )
        return la

    # ---- audit log ----
    def list_audit_log(
        self,
        actor_user_id: str | None,
        actor_role: str | None,
        action: str | None = None,
        actor_role_filter: str | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        if actor_role != "admin":
            raise PermissionError("Only admin can view audit log")
        self._audit(actor_user_id, actor_role, "audit_log_view", resource_type="audit_log")
        return self.audit.list_all(action=action, actor_role=actor_role_filter, limit=limit)
