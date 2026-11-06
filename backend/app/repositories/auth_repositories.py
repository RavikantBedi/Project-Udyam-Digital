"""Repository additions for auth, OTP, assignments, audit tables."""

from sqlmodel import Session, select

from app.models.models import AuditLog, LeadAssignment, OtpCode, RefreshToken, User


class RefreshTokenRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, user_id: str, token_hash: str, expires_at, device_info: str | None, ip_address: str | None) -> RefreshToken:
        rt = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_info=device_info,
            ip_address=ip_address,
        )
        self.session.add(rt)
        self.session.commit()
        self.session.refresh(rt)
        return rt

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.session.exec(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).first()

    def revoke(self, token_hash: str) -> None:
        rt = self.get_by_hash(token_hash)
        if rt and not rt.revoked_at:
            rt.revoked_at = __import__("datetime").datetime.now(__import__("datetime").UTC)
            self.session.add(rt)
            self.session.commit()

    def revoke_all_for_user(self, user_id: str) -> None:
        rts = self.session.exec(select(RefreshToken).where(RefreshToken.user_id == user_id)).all()
        now = __import__("datetime").datetime.now(__import__("datetime").UTC)
        for rt in rts:
            if not rt.revoked_at:
                rt.revoked_at = now
                self.session.add(rt)
        self.session.commit()

    def revoke_expired(self) -> None:
        now = __import__("datetime").datetime.now(__import__("datetime").UTC)
        rts = self.session.exec(select(RefreshToken).where(RefreshToken.expires_at < now)).all()
        for rt in rts:
            if not rt.revoked_at:
                rt.revoked_at = now
                self.session.add(rt)
        self.session.commit()


class OtpCodeRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, purpose: str, target: str, code_hash: str, expires_at) -> OtpCode:
        otp = OtpCode(
            purpose=purpose,
            target=target,
            code_hash=code_hash,
            expires_at=expires_at,
        )
        self.session.add(otp)
        self.session.commit()
        self.session.refresh(otp)
        return otp

    def get_by_target_and_purpose(self, target: str, purpose: str) -> OtpCode | None:
        return self.session.exec(
            select(OtpCode)
            .where(OtpCode.target == target)
            .where(OtpCode.purpose == purpose)
            .where(OtpCode.used_at.is_(None))
            .order_by(OtpCode.created_at.desc())
        ).first()

    def mark_used(self, otp: OtpCode) -> None:
        otp.used_at = __import__("datetime").datetime.now(__import__("datetime").UTC)
        self.session.add(otp)
        self.session.commit()

    def increment_attempts(self, otp: OtpCode) -> None:
        otp.attempts = (otp.attempts or 0) + 1
        self.session.add(otp)
        self.session.commit()

    def cleanup_expired(self) -> None:
        now = __import__("datetime").datetime.now(__import__("datetime").UTC)
        self.session.exec(
            select(OtpCode).where(OtpCode.expires_at < now)
        )  # noqa: B009 — soft delete not implemented; expired rows remain for audit


class LeadAssignmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, lead_id: str, assignee_type: str, assignee_id: str, assigned_by: str, attribution_tag: str, outcome: str | None) -> LeadAssignment:
        la = LeadAssignment(
            lead_id=lead_id,
            assignee_type=assignee_type,
            assignee_id=assignee_id,
            assigned_by=assigned_by,
            attribution_tag=attribution_tag,
            outcome=outcome,
        )
        self.session.add(la)
        self.session.commit()
        self.session.refresh(la)
        return la

    def list_for_assignee(self, assignee_id: str) -> list[LeadAssignment]:
        return self.session.exec(
            select(LeadAssignment).where(LeadAssignment.assignee_id == assignee_id)
        ).all()

    def list_all(self) -> list[LeadAssignment]:
        return self.session.exec(select(LeadAssignment)).all()

    def update_outcome(self, assignment_id: int, outcome: str) -> LeadAssignment | None:
        la = self.session.exec(
            select(LeadAssignment).where(LeadAssignment.id == assignment_id)
        ).first()
        if not la:
            return None
        la.outcome = outcome
        la.updated_at = __import__("datetime").datetime.now(__import__("datetime").UTC)
        self.session.add(la)
        self.session.commit()
        self.session.refresh(la)
        return la


class AuditLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        actor_id: str | None,
        actor_role: str | None,
        action: str,
        resource_type: str | None,
        resource_id: str | None,
        ip_address: str | None,
        before_hash: str | None,
        after_hash: str | None,
    ) -> AuditLog:
        log = AuditLog(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            before_hash=before_hash,
            after_hash=after_hash,
        )
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log

    def list_all(
        self,
        action: str | None = None,
        actor_role: str | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        query = select(AuditLog).order_by(AuditLog.created_at.desc())
        if action:
            query = query.where(AuditLog.action == action)
        if actor_role:
            query = query.where(AuditLog.actor_role == actor_role)
        return self.session.exec(query.limit(limit)).all()


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        return self.session.exec(select(User).where(User.email == email)).first()

    def get_by_id(self, user_id: str) -> User | None:
        return self.session.exec(select(User).where(User.user_id == user_id)).first()

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def save(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def list_all(self) -> list[User]:
        return self.session.exec(select(User)).all()
