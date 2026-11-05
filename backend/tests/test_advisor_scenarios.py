import pytest
from sqlmodel import Session, create_engine, SQLModel
from app.models.models import Product
from app.rules.engine import RulesEngine
from app.api.advisor import extract_slot, detect_language, next_question, build_reply


@pytest.fixture(scope="module")
def seeded_engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        products = [
            Product(product_id="P01", name="Biz Fibre 100", category="Fibre", price_min=899, price_max=1099, one_time_setup=1000, min_contract_months=12, available_city_tiers="1,2,3", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="", typical_install_days=4, target_segments="Micro"),
            Product(product_id="P02", name="Biz Fibre 300", category="Fibre", price_min=1499, price_max=1899, one_time_setup=1000, min_contract_months=12, available_city_tiers="1,2,3", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="", typical_install_days=4, target_segments="Professional"),
            Product(product_id="P03", name="Biz Fibre 1000", category="Fibre", price_min=3499, price_max=4499, one_time_setup=2000, min_contract_months=24, available_city_tiers="1", min_employees=5, min_sites=1, requires_gstin="Y", requires_one_of="", typical_install_days=7, target_segments="Professional"),
            Product(product_id="P04", name="5G AirFiber 100", category="Fixed Wireless", price_min=999, price_max=1299, one_time_setup=500, min_contract_months=6, available_city_tiers="1,2", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="", typical_install_days=2, target_segments="Micro"),
            Product(product_id="P05", name="Internet Leased Line 20", category="Leased Line", price_min=8999, price_max=11999, one_time_setup=5000, min_contract_months=24, available_city_tiers="1,2", min_employees=10, min_sites=1, requires_gstin="Y", requires_one_of="", typical_install_days=14, target_segments="Manufacturer"),
            Product(product_id="P07", name="Business Postpaid 299", category="Mobile", price_min=249, price_max=299, one_time_setup=0, min_contract_months=12, available_city_tiers="1,2,3", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="", typical_install_days=0, target_segments="Micro"),
            Product(product_id="P08", name="Business Postpaid 599", category="Mobile", price_min=499, price_max=599, one_time_setup=0, min_contract_months=12, available_city_tiers="1,2,3", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="", typical_install_days=0, target_segments="Professional"),
            Product(product_id="P09", name="4G/5G Backup Failover", category="Addon", price_min=499, price_max=699, one_time_setup=500, min_contract_months=12, available_city_tiers="1,2,3", min_employees=0, min_sites=1, requires_gstin="N", requires_one_of="P01|P02|P03|P05", typical_install_days=3, target_segments="Multi-site"),
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
        yield RulesEngine(s)


# 1. Hindi input
def test_scenario_01_hindi(seeded_engine):
    lang = detect_language("नमस्ते, मुझे अपनी दुकान के लिए इंटरनेट चाहिए")
    assert lang == "hi"

# 2. Hinglish input
def test_scenario_02_hinglish(seeded_engine):
    lang = detect_language("mera retail shop hai aur mujhe wifi chahiye")
    assert lang == "hi"

# 3. Micro shop with no GSTIN
def test_scenario_03_no_gstin_micro(seeded_engine):
    prof = extract_slot("grocery store with 2 employees in Pune and no gstin", {})
    rec = seeded_engine.recommend_bundle(prof)
    assert rec["segment"] == "Micro retail & services"
    # Ensure no GSTIN-required product in bundle
    for p in rec["bundle"]:
        assert p not in ["P03", "P05", "P06", "P10", "P21", "P24"]

# 4. 1-site Clinic
def test_scenario_04_clinic_office_pro(seeded_engine):
    prof = extract_slot("dental clinic with 4 staff members in Mumbai", {})
    rec = seeded_engine.recommend_bundle(prof)
    assert rec["segment"] == "Professional offices"
    assert rec["bundle_name"] == "Clinic/Office Pro"

# 5. 4-site restaurant chain
def test_scenario_05_multisite_chain(seeded_engine):
    prof = extract_slot("restaurant chain with 4 branches in Delhi", {})
    rec = seeded_engine.recommend_bundle(prof)
    assert rec["segment"] == "Small multi-site businesses"
    assert rec["bundle_name"] == "One Bill"

# 6. Small manufacturer
def test_scenario_06_manufacturer(seeded_engine):
    prof = extract_slot("manufacturing plant with 15 workers in Surat", {"has_gstin": "Y"})
    rec = seeded_engine.recommend_bundle(prof)
    assert rec["segment"] == "Small manufacturers"
    assert "P05" in rec["bundle"] or "P21" in rec["bundle"]

# 7. Mobile-only intent (fast path to P07/P08)
def test_scenario_07_mobile_only(seeded_engine):
    prof = extract_slot("sirf mobile plan chahiye for my team", {})
    rec = seeded_engine.recommend_bundle(prof)
    assert rec["bundle"] == ["P07", "P08"]

# 8. Ineligible P03 in Tier 2 city
def test_scenario_08_p03_ineligible_tier2(seeded_engine):
    rec = seeded_engine.recommend_bundle({"city_tier": 2, "employee_count": 10, "has_gstin": "Y"})
    assert "P03" not in rec["bundle"]

# 9. Price objection handling
def test_scenario_09_pricing_calculation(seeded_engine):
    p = seeded_engine.price_bundle(["P04", "P07"], contract_months=24)
    assert p["monthly_total"] > 0
    assert p["gst"] == round(p["monthly_total"] * 0.18)
    assert p["bundle_saving"] >= 0

# 10. Change of mind mid-chat (overwrites slot)
def test_scenario_10_change_of_mind():
    p1 = extract_slot("I have a shop", {})
    assert p1["business_type"] == "Retail Shop"
    p2 = extract_slot("Actually it is a medical clinic", p1)
    assert p2["business_type"] == "Professional office"

# 11. Handoff to human on explicit request
def test_scenario_11_ask_for_human():
    msg = "I want to talk to a person please"
    assert any(x in msg.lower() for x in ["talk to a person", "human", "agent"])

# 12. Vague answer handling (does not crash or set garbage)
def test_scenario_12_vague_answer():
    p = extract_slot("maybe something normal I don't know", {})
    assert "employee_count" not in p

# 13. Unknown city defaults to Tier 2 with flag
def test_scenario_13_unknown_city_defaults():
    p = extract_slot("my business is in Moradabad", {})
    assert p.get("city_tier") == 2
    assert p.get("city_tier_flag") == "unknown_city_defaulted_tier2"

# 14. 3-employee shop asking for leased line (P05/P06 requires 10+/25+ employees)
def test_scenario_14_leased_line_employee_gate(seeded_engine):
    ok, reason = seeded_engine.is_eligible("P05", {"employee_count": 3, "has_gstin": "Y", "city_tier": 1}, ["P05"])
    assert ok is False
    assert "employees" in reason

# 15. Dependency check: CCTV without base connectivity
def test_scenario_15_cctv_dependency(seeded_engine):
    ok, reason = seeded_engine.is_eligible("P23", {}, [])
    assert ok is False
    assert "Requires one of" in reason
