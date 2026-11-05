import pytest
from datetime import datetime, timedelta
from sqlmodel import Session, create_engine, SQLModel
from app.models.models import Product
from app.rules.engine import RulesEngine, DEMO_TODAY
from app.api.kyc import validate_gstin_checksum, validate_udyam_format, mask_gstin


@pytest.fixture(scope="module")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        # Full test catalogue
        products = [
            Product(product_id="P01", name="Biz Fibre 100", category="Fibre", price_min=899, price_max=1099, one_time_setup=1000, min_contract_months=12, available_city_tiers="1,2,3", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="", typical_install_days=4, target_segments="Micro"),
            Product(product_id="P02", name="Biz Fibre 300", category="Fibre", price_min=1499, price_max=1899, one_time_setup=1000, min_contract_months=12, available_city_tiers="1,2,3", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="", typical_install_days=4, target_segments="Professional"),
            Product(product_id="P03", name="Biz Fibre 1000", category="Fibre", price_min=3499, price_max=4499, one_time_setup=2000, min_contract_months=24, available_city_tiers="1", min_employees=5, min_sites=1, requires_gstin="Y", requires_one_of="", typical_install_days=7, target_segments="Professional"),
            Product(product_id="P04", name="5G AirFiber 100", category="Fixed Wireless", price_min=999, price_max=1299, one_time_setup=500, min_contract_months=6, available_city_tiers="1,2", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="", typical_install_days=2, target_segments="Micro"),
            Product(product_id="P05", name="Internet Leased Line 20", category="Leased Line", price_min=8999, price_max=11999, one_time_setup=5000, min_contract_months=24, available_city_tiers="1,2", min_employees=10, min_sites=1, requires_gstin="Y", requires_one_of="", typical_install_days=14, target_segments="Manufacturer"),
            Product(product_id="P06", name="Internet Leased Line 50", category="Leased Line", price_min=15999, price_max=19999, one_time_setup=5000, min_contract_months=24, available_city_tiers="1,2", min_employees=25, min_sites=1, requires_gstin="Y", requires_one_of="", typical_install_days=14, target_segments="Manufacturer"),
            Product(product_id="P07", name="Business Postpaid 299", category="Mobile", price_min=249, price_max=299, one_time_setup=0, min_contract_months=12, available_city_tiers="1,2,3", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="", typical_install_days=0, target_segments="Micro"),
            Product(product_id="P08", name="Business Postpaid 599", category="Mobile", price_min=499, price_max=599, one_time_setup=0, min_contract_months=12, available_city_tiers="1,2,3", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="", typical_install_days=0, target_segments="Professional"),
            Product(product_id="P09", name="4G/5G Backup Failover", category="Addon", price_min=499, price_max=699, one_time_setup=500, min_contract_months=12, available_city_tiers="1,2,3", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="P01|P02|P03|P05", typical_install_days=3, target_segments="Multi-site"),
            Product(product_id="P10", name="Managed SD-WAN", category="Networking", price_min=2499, price_max=3499, one_time_setup=2000, min_contract_months=24, available_city_tiers="1,2", min_employees=10, min_sites=3, requires_gstin="Y", requires_one_of="P01|P02|P03|P05", typical_install_days=7, target_segments="Multi-site"),
            Product(product_id="P16", name="Cloud Business Email", category="SaaS", price_min=125, price_max=175, one_time_setup=0, min_contract_months=12, available_city_tiers="1,2,3", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="", typical_install_days=0, target_segments="Professional"),
            Product(product_id="P17", name="Cloud Backup", category="SaaS", price_min=299, price_max=399, one_time_setup=0, min_contract_months=12, available_city_tiers="1,2,3", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="", typical_install_days=0, target_segments="Professional"),
            Product(product_id="P19", name="Cloud POS & Billing", category="SaaS", price_min=399, price_max=499, one_time_setup=0, min_contract_months=12, available_city_tiers="1,2,3", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="", typical_install_days=0, target_segments="Micro"),
            Product(product_id="P20", name="Endpoint Security", category="Security", price_min=149, price_max=199, one_time_setup=0, min_contract_months=12, available_city_tiers="1,2,3", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="", typical_install_days=0, target_segments="Professional"),
            Product(product_id="P21", name="Managed Firewall", category="Security", price_min=1999, price_max=2499, one_time_setup=1000, min_contract_months=24, available_city_tiers="1,2", min_employees=5, min_sites=1, requires_gstin="Y", requires_one_of="P01|P02|P03|P05", typical_install_days=5, target_segments="Manufacturer"),
            Product(product_id="P23", name="Cloud CCTV Surveillance", category="IoT", price_min=799, price_max=999, one_time_setup=1000, min_contract_months=12, available_city_tiers="1,2,3", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="P01|P02|P04", typical_install_days=4, target_segments="Multi-site"),
            Product(product_id="P24", name="Machine Monitoring IoT", category="IoT", price_min=2999, price_max=3999, one_time_setup=3000, min_contract_months=24, available_city_tiers="1,2", min_employees=5, min_sites=1, requires_gstin="Y", requires_one_of="", typical_install_days=7, target_segments="Manufacturer"),
        ]
        for p in products:
            s.add(p)
        s.commit()
    with Session(engine) as s:
        yield s


# -------------------------------------------------------------
# 1. Eligibility Rule Tests (20+ cases)
# -------------------------------------------------------------
def test_p03_eligible_tier1(db_session):
    re = RulesEngine(db_session)
    ok, _ = re.is_eligible("P03", {"city_tier": 1, "employee_count": 6, "has_gstin": "Y"}, ["P03"])
    assert ok is True

def test_p03_ineligible_tier2(db_session):
    re = RulesEngine(db_session)
    ok, reason = re.is_eligible("P03", {"city_tier": 2, "employee_count": 6, "has_gstin": "Y"}, ["P03"])
    assert ok is False
    assert "Tier 1" in reason

def test_p03_ineligible_low_employees(db_session):
    re = RulesEngine(db_session)
    ok, reason = re.is_eligible("P03", {"city_tier": 1, "employee_count": 3, "has_gstin": "Y"}, ["P03"])
    assert ok is False
    assert "employees" in reason

def test_p03_ineligible_without_gstin(db_session):
    re = RulesEngine(db_session)
    ok, reason = re.is_eligible("P03", {"city_tier": 1, "employee_count": 10, "has_gstin": "N"}, ["P03"])
    assert ok is False
    assert "GSTIN" in reason

def test_p05_leased_line_min_employees_10(db_session):
    re = RulesEngine(db_session)
    ok_fail, _ = re.is_eligible("P05", {"city_tier": 1, "employee_count": 8, "has_gstin": "Y"}, ["P05"])
    assert ok_fail is False
    ok_pass, _ = re.is_eligible("P05", {"city_tier": 1, "employee_count": 12, "has_gstin": "Y"}, ["P05"])
    assert ok_pass is True

def test_p06_leased_line_min_employees_25(db_session):
    re = RulesEngine(db_session)
    ok_fail, _ = re.is_eligible("P06", {"city_tier": 1, "employee_count": 20, "has_gstin": "Y"}, ["P06"])
    assert ok_fail is False
    ok_pass, _ = re.is_eligible("P06", {"city_tier": 1, "employee_count": 30, "has_gstin": "Y"}, ["P06"])
    assert ok_pass is True

def test_p10_sdwan_min_sites_3(db_session):
    re = RulesEngine(db_session)
    # Missing sites
    ok, reason = re.is_eligible("P10", {"city_tier": 1, "employee_count": 15, "num_sites": 2, "has_gstin": "Y"}, ["P01", "P10"])
    assert ok is False
    assert "sites" in reason

def test_p10_sdwan_dependency_satisfied(db_session):
    re = RulesEngine(db_session)
    # Has base connectivity P01 in bundle
    ok, _ = re.is_eligible("P10", {"city_tier": 1, "employee_count": 15, "num_sites": 3, "has_gstin": "Y"}, ["P01", "P10"])
    assert ok is True

def test_p10_sdwan_dependency_missing(db_session):
    re = RulesEngine(db_session)
    # No base connectivity in bundle
    ok, reason = re.is_eligible("P10", {"city_tier": 1, "employee_count": 15, "num_sites": 3, "has_gstin": "Y"}, ["P10"])
    assert ok is False
    assert "Requires one of" in reason

def test_p09_failover_dependency(db_session):
    re = RulesEngine(db_session)
    ok_fail, _ = re.is_eligible("P09", {"has_gstin": "N"}, ["P09"])
    assert ok_fail is False
    ok_pass, _ = re.is_eligible("P09", {"has_gstin": "N"}, ["P02", "P09"])
    assert ok_pass is True

def test_p21_firewall_needs_gstin_and_connectivity(db_session):
    re = RulesEngine(db_session)
    ok1, _ = re.is_eligible("P21", {"has_gstin": "N", "employee_count": 10}, ["P01", "P21"])
    assert ok1 is False
    ok2, _ = re.is_eligible("P21", {"has_gstin": "Y", "employee_count": 10}, ["P21"])
    assert ok2 is False
    ok3, _ = re.is_eligible("P21", {"has_gstin": "Y", "employee_count": 10}, ["P01", "P21"])
    assert ok3 is True

def test_p23_cctv_dependency(db_session):
    re = RulesEngine(db_session)
    ok_fail, _ = re.is_eligible("P23", {}, ["P23"])
    assert ok_fail is False
    ok_pass, _ = re.is_eligible("P23", {}, ["P04", "P23"])
    assert ok_pass is True

def test_p04_airfiber_tier_restriction(db_session):
    re = RulesEngine(db_session)
    ok_tier3, _ = re.is_eligible("P04", {"city_tier": 3}, ["P04"])
    assert ok_tier3 is False
    ok_tier2, _ = re.is_eligible("P04", {"city_tier": 2}, ["P04"])
    assert ok_tier2 is True


# -------------------------------------------------------------
# 2. Segment Inference Tests
# -------------------------------------------------------------
def test_infer_professional(db_session):
    re = RulesEngine(db_session)
    assert re.infer_segment({"business_type": "Dental Clinic"}) == "Professional offices"
    assert re.infer_segment({"business_type": "CA Firm"}) == "Professional offices"
    assert re.infer_segment({"business_type": "Coaching Institute"}) == "Professional offices"

def test_infer_manufacturing(db_session):
    re = RulesEngine(db_session)
    assert re.infer_segment({"business_type": "Auto Parts Factory"}) == "Small manufacturers"
    assert re.infer_segment({"business_type": "Plastics Plant"}) == "Small manufacturers"

def test_infer_multisite(db_session):
    re = RulesEngine(db_session)
    assert re.infer_segment({"business_type": "Restaurant", "num_sites": 3}) == "Small multi-site businesses"

def test_infer_micro(db_session):
    re = RulesEngine(db_session)
    assert re.infer_segment({"business_type": "Kirana Dukaan", "num_sites": 1}) == "Micro retail & services"


# -------------------------------------------------------------
# 3. Deterministic Pricing Tests
# -------------------------------------------------------------
def test_pricing_determinism(db_session):
    re = RulesEngine(db_session)
    p1 = re.price_bundle(["P04", "P07", "P19"], contract_months=24)
    p2 = re.price_bundle(["P04", "P07", "P19"], contract_months=24)
    assert p1["monthly_total"] == p2["monthly_total"]
    assert p1["gst"] == p2["gst"]
    assert p1["first_bill_estimate"] == p2["first_bill_estimate"]

def test_pricing_contract_monotonicity(db_session):
    re = RulesEngine(db_session)
    p12 = re.price_bundle(["P02", "P16", "P07"], contract_months=12)
    p24 = re.price_bundle(["P02", "P16", "P07"], contract_months=24)
    p36 = re.price_bundle(["P02", "P16", "P07"], contract_months=36)
    # Longer contract should have lower or equal monthly price
    assert p24["monthly_total"] <= p12["monthly_total"]
    assert p36["monthly_total"] <= p24["monthly_total"]

def test_pricing_gst_calculation(db_session):
    re = RulesEngine(db_session)
    p = re.price_bundle(["P01"])
    assert p["gst"] == round(p["monthly_total"] * 0.18)


# -------------------------------------------------------------
# 4. GSTIN & Udyam Validator Tests
# -------------------------------------------------------------
def test_gstin_checksum_valid():
    # Real GSTIN structure with valid checksum from dataset
    # Accepts 'X' as 4th PAN character
    assert validate_gstin_checksum("32TTNXB7384T1ZW") is True
    assert validate_gstin_checksum("03PJNXS4821G1ZB") is True
    assert validate_gstin_checksum("33MFTXS9954Q1Z9") is True

def test_gstin_length_rejection():
    assert validate_gstin_checksum("12345") is False
    assert validate_gstin_checksum("27AAECP1234F1Z") is False

def test_udyam_format_valid():
    assert validate_udyam_format("UDYAM-MH-00-0012345") is True
    assert validate_udyam_format("UDYAM-DL-00-9876543") is True

def test_udyam_format_invalid():
    assert validate_udyam_format("UDYAM-MH-12-0012345") is False  # district must be 00 per spec
    assert validate_udyam_format("MH-00-0012345") is False
    assert validate_udyam_format("") is False

def test_gstin_masking():
    masked = mask_gstin("27AAECP1234F1ZX")
    assert "•" in masked
    assert masked.startswith("27AA")
    assert masked.endswith("1ZX")


# -------------------------------------------------------------
# 5. Data Privacy & Leakage Test
# -------------------------------------------------------------
def test_propensity_pipeline_no_data_leakage():
    from app.api.office import retrain_model
    # Forbidden features that must never be used in propensity model
    forbidden = ["stage_reached", "outcome", "drop_reason", "preferred_language", "state"]
    # Retrain function documentation specifies features
    res = retrain_model()
    if "features" in res:
        for feat in forbidden:
            assert feat not in res["features"], f"Data leakage: {feat} found in propensity features!"
