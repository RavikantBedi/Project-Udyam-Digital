from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlmodel import Session
from app.core.db import get_session
from app.core.config import get_data_dir, get_settings
from app.models.models import ConsentLedger
import os
import csv
import uuid
import re
from datetime import datetime

router = APIRouter()
settings = get_settings()

GSTIN_MULTIPLIER = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2]
GSTIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def validate_gstin_checksum(gstin: str) -> bool:
    """Validate GSTIN using the standard checksum algorithm. Accept X as the 4th PAN char."""
    if len(gstin) != 15:
        return False
    gstin = gstin.upper()
    # Allow X as 4th char of PAN (position index 5 in GSTIN)
    total = 0
    for i, ch in enumerate(gstin[:-1]):
        if ch not in GSTIN_CHARS:
            # Accept X specifically at position 5 (4th PAN char)
            if i == 5 and ch == "X":
                val = GSTIN_CHARS.index("X") if "X" in GSTIN_CHARS else 33
            else:
                return False
        else:
            val = GSTIN_CHARS.index(ch)
        v = val * GSTIN_MULTIPLIER[i]
        total += (v // 36) + (v % 36)
    check = (36 - (total % 36)) % 36
    return GSTIN_CHARS[check] == gstin[-1]


def validate_udyam_format(number: str) -> bool:
    """Validate UDYAM-XX-00-NNNNNNN format with district code 00."""
    return bool(re.match(r"^UDYAM-[A-Z]{2}-00-\d{7}$", number.strip().upper()))


def mask_gstin(gstin: str) -> str:
    if len(gstin) >= 10:
        return gstin[:4] + "•" * (len(gstin) - 7) + gstin[-3:]
    return "••••••••••••••"


@router.post("/consent")
def consent(data: dict, session: Session = Depends(get_session)):
    ledger = ConsentLedger(
        order_id=data.get("order_id", ""),
        purpose="kyc_verification",
        consent_given=data.get("consent_given", False),
        marketing_consent=data.get("marketing_consent", False),
        language=data.get("language", "hi"),
        consent_hash=str(uuid.uuid4()),
    )
    session.add(ledger)
    session.commit()
    return {"status": "ok", "consent_hash": ledger.consent_hash}


@router.get("/lookup/gstin/{gstin}")
def lookup_gstin(gstin: str):
    gstin_clean = gstin.strip().upper()

    # Format check
    if len(gstin_clean) != 15:
        return {"error": "Invalid GSTIN format (must be 15 characters)", "status": "format_error"}

    # Checksum validation
    if not validate_gstin_checksum(gstin_clean):
        return {"error": "Invalid GSTIN checksum", "status": "checksum_error"}

    # Registry lookup
    path = os.path.join(get_data_dir(), "mock_gstin_registry.csv")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["gstin"].strip().upper() == gstin_clean:
                    result = dict(row)
                    # Mask GSTIN in response (show partial)
                    result["gstin_masked"] = mask_gstin(result["gstin"])
                    result["gstin"] = mask_gstin(result["gstin"])
                    return result
    return {"error": "GSTIN not found in registry", "status": "not_found"}


@router.get("/lookup/udyam/{number}")
def lookup_udyam(number: str):
    num_clean = number.strip().upper()

    if not validate_udyam_format(num_clean):
        return {"error": "Invalid Udyam number format (expected UDYAM-XX-00-NNNNNNN)", "status": "format_error"}

    path = os.path.join(get_data_dir(), "mock_udyam_registry.csv")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["udyam_number"].strip().upper() == num_clean:
                    return row
    return {"error": "Udyam number not found in registry", "status": "not_found"}


@router.post("/kyc/upload")
async def kyc_upload(file: UploadFile = File(...)):
    upload_dir = settings.upload_dir or "./uploads"
    os.makedirs(upload_dir, exist_ok=True)
    fname = f"{uuid.uuid4().hex}_{file.filename}"
    path = os.path.join(upload_dir, fname)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    return {"filename": fname, "status": "uploaded", "size": len(content)}


@router.post("/kyc/validate")
def kyc_validate(data: dict):
    """Run KYC validation checks against submitted data."""
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
        checks.append({"item": "GSTIN format & checksum", "status": "Needs attention", "fix": "GSTIN not provided"})

    # 2. Registry status (Active required)
    if registry_status == "Active":
        checks.append({"item": "Registry status", "status": "Pass", "fix": ""})
    elif registry_status in ("Cancelled", "Suspended"):
        checks.append({
            "item": "Registry status",
            "status": "Failed",
            "fix": f"GSTIN is {registry_status}. Please contact your CA or visit GST portal to resolve.",
        })
    else:
        checks.append({"item": "Registry status", "status": "Needs attention", "fix": "Could not verify registry status"})

    # 3. Udyam format
    if udyam:
        udyam_ok = validate_udyam_format(udyam)
        checks.append({
            "item": "Udyam number format",
            "status": "Pass" if udyam_ok else "Failed",
            "fix": "" if udyam_ok else "Format must be UDYAM-XX-00-NNNNNNN (e.g. UDYAM-MH-00-0012345)",
        })
    else:
        checks.append({"item": "Udyam number format", "status": "Needs attention", "fix": "Udyam number not provided"})

    # 4. Address proof age ≤ 90 days from DEMO_TODAY (2026-07-15)
    demo_today = datetime(2026, 7, 15)
    if address_proof_date:
        try:
            proof_date = datetime.strptime(address_proof_date, "%Y-%m-%d")
            age_days = (demo_today - proof_date).days
            if 0 <= age_days <= 90:
                checks.append({"item": "Address proof age ≤ 90 days", "status": "Pass", "fix": ""})
            else:
                checks.append({
                    "item": "Address proof age ≤ 90 days",
                    "status": "Failed",
                    "fix": f"Address proof is {age_days} days old. Please upload a document dated after {(demo_today.replace(year=2026, month=4, day=16)).strftime('%d %b %Y')}.",
                })
        except ValueError:
            checks.append({"item": "Address proof age ≤ 90 days", "status": "Needs attention", "fix": "Could not parse date from document"})
    else:
        checks.append({"item": "Address proof age ≤ 90 days", "status": "Needs attention", "fix": "Address proof date not extracted"})

    # 5. Name consistency across documents (fuzzy)
    names = [n for n in [name_on_gstin, name_on_udyam, name_on_id] if n]
    if len(names) >= 2:
        # Simple fuzzy: check if first two tokens of each name overlap
        def name_tokens(n):
            return set(n.lower().split())
        base = name_tokens(names[0])
        all_match = all(len(base & name_tokens(n)) >= 1 for n in names[1:])
        checks.append({
            "item": "Name consistency across documents",
            "status": "Pass" if all_match else "Needs attention",
            "fix": "" if all_match else "Business or owner name differs across documents. Please check and re-upload if needed.",
        })
    else:
        checks.append({"item": "Name consistency across documents", "status": "Needs attention", "fix": "Not enough documents to compare names"})

    overall_statuses = [c["status"] for c in checks]
    if "Failed" in overall_statuses:
        overall = "Failed"
    elif "Needs attention" in overall_statuses:
        overall = "Needs attention"
    else:
        overall = "Pass"

    return {"checks": checks, "overall": overall}


@router.post("/esign/otp")
def esign_otp(data: dict):
    """Send simulated e-sign OTP."""
    return {"status": "sent", "demo_otp": "123456", "note": "Simulated for demo — use OTP 123456"}


@router.post("/esign/verify")
def esign_verify(data: dict):
    """Verify simulated e-sign OTP."""
    if str(data.get("otp", "")).strip() == "123456":
        return {"status": "verified", "signed_at": str(datetime.utcnow())}
    return {"status": "failed", "error": "Invalid OTP"}
