"""KYC router — consent, registry lookup, document validation, e-sign simulation."""
import os
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session

from app.core.db import engine, get_session
from app.schemas.schemas import (
    ConsentReq,
    ConsentResp,
    ESIGNOTPResp,
    ESIGNVerifyResp,
    GSTINLookupResp,
    KYCUploadResp,
    UdyamLookupResp,
)
from app.services.ocr import (  # noqa: F401 — re-exported for test compatibility
    mask_gstin,
    validate_gstin_checksum,
    validate_udyam_format,
)
from app.services.services import KYCService

router = APIRouter(prefix="/kyc", tags=["kyc"])


@router.post("/consent", response_model=ConsentResp, status_code=status.HTTP_201_CREATED)
def record_consent(
    req: ConsentReq,
    session: Session = Depends(get_session),
):
    service = KYCService(session)
    ledger = service.record_consent(
        order_id=req.order_id,
        consent_given=req.consent_given,
        marketing_consent=req.marketing_consent,
        language=req.language,
    )
    return ConsentResp(status="ok", consent_hash=ledger.consent_hash)


@router.get("/lookup/gstin/{gstin}", response_model=GSTINLookupResp)
def lookup_gstin(gstin: str, session: Session = Depends(get_session)):
    service = KYCService(session)
    result = service.lookup_gstin(gstin)
    if "error" in result:
        status_code = 404 if result["status"] == "not_found" else 400
        raise HTTPException(status_code=status_code, detail=result["error"])
    return GSTINLookupResp(**result)


@router.get("/lookup/udyam/{number}", response_model=UdyamLookupResp)
def lookup_udyam(number: str, session: Session = Depends(get_session)):
    service = KYCService(session)
    result = service.lookup_udyam(number)
    if "error" in result:
        status_code = 404 if result["status"] == "not_found" else 400
        raise HTTPException(status_code=status_code, detail=result["error"])
    return UdyamLookupResp(**result)


@router.post("/upload", response_model=KYCUploadResp)
async def kyc_upload(file: UploadFile = File(...)):
    upload_dir = "./uploads"
    os.makedirs(upload_dir, exist_ok=True)
    fname = f"{uuid.uuid4().hex}_{file.filename}"
    path = os.path.join(upload_dir, fname)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    return KYCUploadResp(filename=fname, status="uploaded", size=len(content))


@router.post("/validate")
def kyc_validate(
    req: Any,
    session: Session | None = Depends(get_session),
):
    if session is None:
        session = Session(engine)
    service = KYCService(session)
    req_dict = req.model_dump() if hasattr(req, "model_dump") else req
    return service.validate(req_dict)


@router.post("/esign/otp", response_model=ESIGNOTPResp)
def esign_otp():
    return ESIGNOTPResp(status="sent", demo_otp="123456", note="Simulated for demo — use OTP 123456")


@router.post("/esign/verify", response_model=ESIGNVerifyResp)
def esign_verify(otp: str):
    if str(otp).strip() != "123456":
        raise HTTPException(status_code=400, detail="Invalid OTP")
    return ESIGNVerifyResp(status="verified")
