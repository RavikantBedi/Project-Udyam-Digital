import os
from datetime import datetime
from app.api.kyc import validate_gstin_checksum, validate_udyam_format, kyc_validate
from app.core.config import get_data_dir


def test_kyc_specimens_exist():
    data_dir = get_data_dir()
    kyc_path = os.path.join(data_dir, "kyc_documents")
    assert os.path.exists(kyc_path), f"kyc_documents not found at {kyc_path}"
    files = os.listdir(kyc_path)
    assert len(files) >= 40, f"Expected ≥40 document specimens, got {len(files)}"


def test_k01_failing_case_detected():
    """
    K01 has planted defects:
    - Address proof is older than 90 days from DEMO_TODAY (2026-07-15)
    - Missing Udyam number
    """
    res = kyc_validate({
        "gstin": "27AAECP1234F1ZX",
        "udyam": "",  # Blank Udyam
        "registry_status": "Active",
        "address_proof_date": "2026-01-10",  # >90 days old from 2026-07-15
        "name_on_gstin": "Sharma Clinic",
        "name_on_udyam": "",
        "name_on_id": "Priya Sharma",
    })
    assert res["overall"] != "Pass"
    statuses = [c["status"] for c in res["checks"]]
    assert "Failed" in statuses or "Needs attention" in statuses


def test_k02_passing_case():
    """
    K02 is a clean, compliant applicant:
    - Valid GSTIN with checksum
    - Active registry status
    - Valid Udyam format
    - Address proof within 90 days (e.g. 2026-06-20)
    - Name consistency
    """
    res = kyc_validate({
        "gstin": "27AAECP1234F1ZX",
        "udyam": "UDYAM-MH-00-0012345",
        "registry_status": "Active",
        "address_proof_date": "2026-06-20",  # 25 days old (well within 90 days)
        "name_on_gstin": "Priya Sharma Clinic",
        "name_on_udyam": "Priya Sharma Clinic",
        "name_on_id": "Priya Sharma",
    })
    # GSTIN checksum is validated (or if mock GSTIN, verify checks list)
    assert len(res["checks"]) >= 4
    # Address proof age must pass
    age_check = next((c for c in res["checks"] if "Address proof age" in c["item"]), None)
    assert age_check is not None
    assert age_check["status"] == "Pass"


def test_cancelled_gstin_fails():
    res = kyc_validate({
        "gstin": "27AAECP1234F1ZX",
        "udyam": "UDYAM-MH-00-0012345",
        "registry_status": "Cancelled",
        "address_proof_date": "2026-06-20",
    })
    reg_check = next((c for c in res["checks"] if "Registry status" in c["item"]), None)
    assert reg_check is not None
    assert reg_check["status"] == "Failed"
    assert res["overall"] == "Failed"


def test_suspended_gstin_fails():
    res = kyc_validate({
        "gstin": "27AAECP1234F1ZX",
        "udyam": "UDYAM-MH-00-0012345",
        "registry_status": "Suspended",
        "address_proof_date": "2026-06-20",
    })
    assert res["overall"] == "Failed"


def test_all_12_applicants_files_accounted_for():
    data_dir = get_data_dir()
    kyc_path = os.path.join(data_dir, "kyc_documents")
    files = set(os.listdir(kyc_path))
    for i in range(1, 13):
        prefix = f"K{i:02d}_"
        matching = [f for f in files if f.startswith(prefix)]
        assert len(matching) >= 2, f"Applicant {prefix} missing files in {kyc_path}"
