"""Auth router — signup, signin, refresh, signout, password reset, OTP, me."""
import hashlib
import secrets as _secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import jwt
from sqlmodel import Session

from app.core.config import get_settings
from app.core.db import get_session
from app.repositories import OtpCodeRepository
from app.schemas.schemas import (
    ChangePasswordReq,
    ForgotPasswordReq,
    Message,
    OtpSendReq,
    OtpVerifyReq,
    RefreshReq,
    ResetPasswordReq,
    SigninReq,
    SignoutReq,
    SignupReq,
    TokenResp,
    UserCreateReq,
    UserResponse,
    UserUpdateRoleReq,
)
from app.security.auth import (
    generate_csrf_token,
    get_current_user,
    require_role,
    tokens_for_user,
    verify_csrf_token,
)
from app.services.admin_service import AdminService
from app.services.auth_service import AuthService

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = settings.app_env == "production"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/api/auth",
    )
    response.set_cookie(
        key="csrf_token",
        value=generate_csrf_token(),
        httponly=False,
        secure=secure,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/auth")
    response.delete_cookie(key="csrf_token", path="/")


@router.post("/signup", response_model=TokenResp, status_code=status.HTTP_201_CREATED)
def signup(
    req: SignupReq,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    service = AuthService(session)
    try:
        user = service.signup(
            email=req.email,
            phone=req.phone,
            business_name=req.business_name,
            password=req.password,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from None
    token_pair = tokens_for_user(user)
    _set_auth_cookies(response, token_pair.access_token, token_pair.refresh_token)
    return TokenResp(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/signin", response_model=TokenResp)
def signin(
    req: SigninReq,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    service = AuthService(session)
    try:
        user, refresh_plain = service.signin(
            email=req.email,
            password=req.password,
            ip_address=request.client.host if request.client else None,
            device_info=request.headers.get("user-agent"),
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid email or password") from None
    token_pair = tokens_for_user(user)
    _set_auth_cookies(response, token_pair.access_token, refresh_plain)
    return TokenResp(
        access_token=token_pair.access_token,
        refresh_token=refresh_plain,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResp)
def refresh(
    req: RefreshReq,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    service = AuthService(session)
    try:
        access, new_refresh = service.refresh(
            refresh_token=req.refresh_token,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as err:
        raise HTTPException(status_code=401, detail=str(err)) from None
    payload = jwt.decode(access, settings.jwt_secret, algorithms=[settings.algorithm])
    user = service.users.get_by_id(payload.get("sub"))
    _set_auth_cookies(response, access, new_refresh)
    return TokenResp(
        access_token=access,
        refresh_token=new_refresh,
        user=UserResponse.model_validate(user),
    )


@router.post("/signout", response_model=Message)
def signout(
    req: SignoutReq,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    current_user: UserResponse = Depends(get_current_user),
):
    service = AuthService(session)
    service.signout(
        refresh_token=req.refresh_token,
        user_id=current_user.user_id,
        ip_address=request.client.host if request.client else None,
    )
    _clear_auth_cookies(response)
    return Message(message="Signed out")


@router.post("/signout-all", response_model=Message)
def signout_all(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    current_user: UserResponse = Depends(get_current_user),
):
    service = AuthService(session)
    service.signout_all(
        user_id=current_user.user_id,
        ip_address=request.client.host if request.client else None,
    )
    _clear_auth_cookies(response)
    return Message(message="All sessions signed out")


@router.get("/me", response_model=UserResponse)
def me(current_user: UserResponse = Depends(get_current_user)):
    return current_user


@router.post("/change-password", response_model=Message)
def change_password(
    req: ChangePasswordReq,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    current_user: UserResponse = Depends(get_current_user),
):
    verify_csrf_token(request, request.headers.get("x-csrf-token"))
    service = AuthService(session)
    user = service.users.get_by_id(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        service.change_password(
            user=user,
            current_password=req.current_password,
            new_password=req.new_password,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from None
    _clear_auth_cookies(response)
    return Message(message="Password changed — please sign in again")


@router.post("/forgot-password", response_model=Message)
def forgot_password(
    req: ForgotPasswordReq,
    request: Request,
    session: Session = Depends(get_session),
):
    service = AuthService(session)
    service.forgot_password(
        email=req.email,
        ip_address=request.client.host if request.client else None,
    )
    return Message(message="If an account exists, a reset code has been sent to your email")


@router.post("/reset-password", response_model=Message)
def reset_password(
    req: ResetPasswordReq,
    request: Request,
    session: Session = Depends(get_session),
):
    service = AuthService(session)
    try:
        service.reset_password(
            email=req.email,
            code=req.code,
            new_password=req.new_password,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from None
    return Message(message="Password reset successful — please sign in")


@router.post("/otp/send", response_model=Message)
def otp_send(
    req: OtpSendReq,
    request: Request,
    session: Session = Depends(get_session),
):
    service = AuthService(session)
    code = f"{_secrets.randbelow(1000000):06d}"
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.otp_expire_minutes)
    otp_repo = OtpCodeRepository(session)
    existing = otp_repo.get_by_target_and_purpose(req.target, req.purpose)
    if existing:
        existing.used_at = datetime.now(UTC)
        session.add(existing)
    otp_repo.create(req.purpose, req.target, code_hash, expires_at)
    service.provider.send(req.target, code, req.channel)
    return Message(message="OTP sent — check your email or phone")


@router.post("/otp/verify", response_model=Message)
def otp_verify(
    req: OtpVerifyReq,
    request: Request,
    session: Session = Depends(get_session),
):
    service = AuthService(session)
    try:
        service.verify_otp(
            target=req.target,
            code=req.code,
            purpose=req.purpose,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from None
    return Message(message="OTP verified successfully")


# ---------------------------------------------------------------------------
# Admin user management (admin only)
# ---------------------------------------------------------------------------
@router.post(
    "/admin/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def admin_create_user(
    req: UserCreateReq,
    request: Request,
    session: Session = Depends(get_session),
    current_user: UserResponse = Depends(require_role(["admin"])),
):
    service = AdminService(session)
    try:
        user = service.create_user(
            actor_user_id=current_user.user_id,
            actor_role=current_user.role,
            email=req.email,
            phone=req.phone,
            business_name=req.business_name,
            password=req.password,
            role=req.role,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from None
    return UserResponse.model_validate(user)


@router.get("/admin/users", response_model=list[UserResponse])
def admin_list_users(
    session: Session = Depends(get_session),
    current_user: UserResponse = Depends(require_role(["admin"])),
):
    service = AdminService(session)
    users = service.list_users(actor_user_id=current_user.user_id, actor_role=current_user.role)
    return [UserResponse.model_validate(u) for u in users]


@router.patch(
    "/admin/users/{user_id}/role", response_model=UserResponse
)
def admin_update_user_role(
    user_id: str,
    req: UserUpdateRoleReq,
    request: Request,
    session: Session = Depends(get_session),
    current_user: UserResponse = Depends(require_role(["admin"])),
):
    service = AdminService(session)
    try:
        user = service.update_user_role(
            actor_user_id=current_user.user_id,
            actor_role=current_user.role,
            user_id=user_id,
            new_role=req.role,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from None
    except PermissionError as err:
        raise HTTPException(status_code=403, detail=str(err)) from None
    return UserResponse.model_validate(user)
