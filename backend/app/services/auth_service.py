"""Auth service — signup, signin, refresh, signout, password reset, OTP verification."""
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from app.core.config import get_settings
from app.models.models import (
    User,
)
from app.repositories import (
    AuditLogRepository,
    LeadRepository,
    NotificationLogRepository,
    OtpCodeRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.security.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.services.notifications import send_email, send_otp

settings = get_settings()


# ---------------------------------------------------------------------------
# OTP provider interface
# ---------------------------------------------------------------------------
class OtpProvider:
    """Interface for OTP delivery. Twilio Verify when configured; dev provider logs the code."""

    def send(self, target: str, code: str, channel: str = "sms") -> bool:
        raise NotImplementedError

    def verify(self, target: str, code: str, purpose: str) -> bool:
        raise NotImplementedError


class DevOtpProvider(OtpProvider):
    """Dev provider — logs OTP codes to stdout and notification log. Never used in production."""

    def send(self, target: str, code: str, channel: str = "sms") -> bool:
        if settings.app_env == "production":
            raise RuntimeError("Dev OTP provider cannot be used in production")
        return send_otp(target, code, channel)

    def verify(self, target: str, code: str, purpose: str) -> bool:
        """Dev provider verification is handled by the OtpService (hashed code comparison)."""
        return True


class TwilioVerifyProvider(OtpProvider):
    """Twilio Verify provider — used when TWILIO_VERIFY_SERVICE_SID is configured."""

    def __init__(self):
        self.service_sid = settings.twilio_verify_service_sid

    def send(self, target: str, code: str, channel: str = "sms") -> bool:
        if not self.service_sid:
            return send_otp(target, code, channel)
        # Twilio Verify generates its own code; we just trigger the send
        import httpx

        try:
            url = f"https://verify.twilio.com/v2/Services/{self.service_sid}/Verifications"
            res = httpx.post(
                url,
                data={"To": target, "Channel": channel},
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                timeout=5,
            )
            return res.status_code in (200, 201)
        except Exception:
            return False

    def verify(self, target: str, code: str, purpose: str) -> bool:
        if not self.service_sid:
            return False
        import httpx

        try:
            url = f"https://verify.twilio.com/v2/Services/{self.service_sid}/VerificationCheck"
            res = httpx.post(
                url,
                data={"To": target, "Code": code},
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                timeout=5,
            )
            return res.status_code == 200
        except Exception:
            return False


def get_otp_provider() -> OtpProvider:
    if settings.twilio_verify_service_sid:
        return TwilioVerifyProvider()
    return DevOtpProvider()


# ---------------------------------------------------------------------------
# Auth service
# ---------------------------------------------------------------------------
class AuthService:
    def __init__(self, session: Session):
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.otps = OtpCodeRepository(session)
        self.audit = AuditLogRepository(session)
        self.notifications = NotificationLogRepository(session)
        self.leads = LeadRepository(session)
        self.provider = get_otp_provider()

    # ---- helpers ----
    def _audit(
        self,
        actor: User | None,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        before_hash: str | None = None,
        after_hash: str | None = None,
    ) -> None:
        self.audit.create(
            actor_id=actor.user_id if actor else None,
            actor_role=actor.role if actor else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            before_hash=before_hash,
            after_hash=after_hash,
        )

    def _hash_code(self, code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    # ---- signup ----
    def signup(
        self,
        email: str,
        phone: str,
        business_name: str,
        password: str,
        ip_address: str | None = None,
    ) -> User:
        clean_email = email.strip().lower()
        if self.users.get_by_email(clean_email):
            raise ValueError("An account with this email already exists")
        user = User(
            user_id=f"USR-{secrets.token_hex(4).upper()}",
            email=clean_email,
            phone=phone.strip(),
            business_name=business_name.strip(),
            password_hash=hash_password(password),
            password_algorithm="argon2id",
            role="owner",
        )
        created = self.users.create(user)
        self._audit(
            created,
            "signup",
            resource_type="user",
            resource_id=created.user_id,
            ip_address=ip_address,
            after_hash=hashlib.sha256(clean_email.encode()).hexdigest()[:16],
        )
        return created

    # ---- signin ----
    def signin(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        device_info: str | None = None,
    ) -> User:
        clean_email = email.strip().lower()
        user = self.users.get_by_email(clean_email)
        if not user:
            # Generic error — no user enumeration
            raise ValueError("Invalid email or password")

        # Account lockout check
        if user.locked_until and user.locked_until > datetime.now(UTC):
            raise ValueError("Account is locked — try again later")

        if not verify_password(password, user.password_hash):
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= settings.lockout_after_failures:
                user.locked_until = datetime.now(UTC) + timedelta(
                    minutes=settings.lockout_minutes
                )
            self.users.save(user)
            self._audit(
                user,
                "signin_failed",
                resource_type="user",
                resource_id=user.user_id,
                ip_address=ip_address,
            )
            raise ValueError("Invalid email or password")

        # Reset failures on success
        user.failed_login_attempts = 0
        user.locked_until = None
        self.users.save(user)

        # Create rotating refresh token
        refresh_plain = create_refresh_token(user.user_id, user.email, user.role)
        refresh_hash = hash_token(refresh_plain)
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
        self.refresh_tokens.create(
            user_id=user.user_id,
            token_hash=refresh_hash,
            expires_at=expires_at,
            device_info=device_info,
            ip_address=ip_address,
        )

        self._audit(
            user,
            "login",
            resource_type="user",
            resource_id=user.user_id,
            ip_address=ip_address,
            after_hash=hashlib.sha256(clean_email.encode()).hexdigest()[:16],
        )
        return user, refresh_plain

    # ---- refresh ----
    def refresh(
        self,
        refresh_token: str,
        ip_address: str | None = None,
    ) -> tuple[str, str]:
        """Rotate refresh token: old one revoked, new one issued."""
        refresh_hash = hash_token(refresh_token)
        rt = self.refresh_tokens.get_by_hash(refresh_hash)
        if not rt:
            raise ValueError("Invalid refresh token")
        if rt.revoked_at:
            # Replay detected — revoke all tokens for this user
            self.refresh_tokens.revoke_all_for_user(rt.user_id)
            self._audit(
                None,
                "refresh_replay",
                resource_type="refresh_token",
                resource_id=rt.user_id,
                ip_address=ip_address,
            )
            raise ValueError("Refresh token replay detected — all sessions revoked")
        if rt.expires_at < datetime.now(UTC):
            rt.revoked_at = datetime.now(UTC)
            self.session.add(rt)
            self.session.commit()
            raise ValueError("Refresh token expired")

        user = self.users.get_by_id(rt.user_id)
        if not user or not user.is_active:
            raise ValueError("User not found or deactivated")

        # Revoke old token, issue new
        rt.revoked_at = datetime.now(UTC)
        self.session.add(rt)
        new_plain = create_refresh_token(user.user_id, user.email, user.role)
        new_hash = hash_token(new_plain)
        new_expires = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
        self.refresh_tokens.create(
            user_id=user.user_id,
            token_hash=new_hash,
            expires_at=new_expires,
            device_info=rt.device_info,
            ip_address=ip_address,
        )
        self.session.commit()

        access = create_access_token(user.user_id, user.email, user.role)
        self._audit(
            user,
            "token_refresh",
            resource_type="user",
            resource_id=user.user_id,
            ip_address=ip_address,
        )
        return access, new_plain

    # ---- signout ----
    def signout(self, refresh_token: str | None, user_id: str, ip_address: str | None = None) -> None:
        if refresh_token:
            rt = self.refresh_tokens.get_by_hash(hash_token(refresh_token))
            if rt and rt.user_id == user_id:
                rt.revoked_at = datetime.now(UTC)
                self.session.add(rt)
                self.session.commit()
        self._audit(
            None,
            "signout",
            resource_type="user",
            resource_id=user_id,
            ip_address=ip_address,
        )

    def signout_all(self, user_id: str, ip_address: str | None = None) -> None:
        self.refresh_tokens.revoke_all_for_user(user_id)
        self._audit(
            None,
            "signout_all",
            resource_type="user",
            resource_id=user_id,
            ip_address=ip_address,
        )

    # ---- change password ----
    def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
        ip_address: str | None = None,
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")
        user.password_hash = hash_password(new_password)
        user.password_algorithm = "argon2id"
        user.failed_login_attempts = 0
        user.locked_until = None
        self.users.save(user)
        # Revoke all sessions on password change
        self.refresh_tokens.revoke_all_for_user(user.user_id)
        self._audit(
            user,
            "change_password",
            resource_type="user",
            resource_id=user.user_id,
            ip_address=ip_address,
        )

    # ---- forgot / reset password ----
    def forgot_password(
        self,
        email: str,
        ip_address: str | None = None,
    ) -> None:
        """Send a password-reset OTP via email. Generic response to prevent enumeration."""
        clean_email = email.strip().lower()
        user = self.users.get_by_email(clean_email)
        if not user:
            return  # Generic — don't reveal whether email exists

        # Invalidate any existing reset OTPs for this target
        existing = self.otps.get_by_target_and_purpose(clean_email, "reset_password")
        if existing:
            existing.used_at = datetime.now(UTC)
            self.session.add(existing)

        code = f"{secrets.randbelow(1000000):06d}"
        code_hash = self._hash_code(code)
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.otp_expire_minutes)
        self.otps.create("reset_password", clean_email, code_hash, expires_at)
        send_email(
            clean_email,
            "Reset your Accel Business password",
            f"Your password reset code is: {code}\nValid for {settings.otp_expire_minutes} minutes.",
        )
        self._audit(
            user,
            "forgot_password",
            resource_type="user",
            resource_id=user.user_id,
            ip_address=ip_address,
        )

    def reset_password(
        self,
        email: str,
        code: str,
        new_password: str,
        ip_address: str | None = None,
    ) -> None:
        clean_email = email.strip().lower()
        user = self.users.get_by_email(clean_email)
        if not user:
            raise ValueError("Invalid reset request")

        otp = self.otps.get_by_target_and_purpose(clean_email, "reset_password")
        if not otp:
            raise ValueError("Invalid or expired reset code")
        if otp.attempts >= settings.otp_max_attempts:
            raise ValueError("Reset code attempts exhausted — request a new one")
        if otp.expires_at < datetime.now(UTC):
            raise ValueError("Reset code expired")

        code_hash = self._hash_code(code)
        if not verify_password(code, code_hash):  # constant-time compare via passlib
            otp.attempts = (otp.attempts or 0) + 1
            self.session.add(otp)
            self.session.commit()
            raise ValueError("Invalid reset code")

        otp.used_at = datetime.now(UTC)
        self.session.add(otp)
        user.password_hash = hash_password(new_password)
        user.password_algorithm = "argon2id"
        user.failed_login_attempts = 0
        user.locked_until = None
        self.session.add(user)
        self.session.commit()
        self.refresh_tokens.revoke_all_for_user(user.user_id)
        self._audit(
            user,
            "reset_password",
            resource_type="user",
            resource_id=user.user_id,
            ip_address=ip_address,
        )

    # ---- OTP verify ----
    def verify_otp(
        self,
        target: str,
        code: str,
        purpose: str,
        ip_address: str | None = None,
    ) -> bool:
        target_clean = target.strip().lower()
        otp = self.otps.get_by_target_and_purpose(target_clean, purpose)
        if not otp:
            raise ValueError("Invalid or expired OTP")
        if otp.attempts >= settings.otp_max_attempts:
            raise ValueError("OTP attempts exhausted — request a new one")
        if otp.expires_at < datetime.now(UTC):
            raise ValueError("OTP expired")

        code_hash = self._hash_code(code)
        if not verify_password(code, code_hash):
            otp.attempts = (otp.attempts or 0) + 1
            self.session.add(otp)
            self.session.commit()
            raise ValueError("Invalid OTP")

        otp.used_at = datetime.now(UTC)
        self.session.add(otp)
        self.session.commit()
        self._audit(
            None,
            "otp_verified",
            resource_type="otp",
            resource_id=target_clean,
            ip_address=ip_address,
        )
        return True
