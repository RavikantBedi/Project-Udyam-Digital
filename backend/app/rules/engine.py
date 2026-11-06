from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.models import Product

_settings = get_settings()
DEMO_TODAY = datetime.strptime(_settings.demo_today, "%Y-%m-%d")

SEGMENT_TEMPLATES: dict[str, list[str]] = {
    "Micro retail & services": ["P04", "P07", "P19"],
    "Professional offices": ["P02", "P16", "P07", "P20", "P17"],
    "Small multi-site businesses": ["P01", "P09", "P08", "P23", "P19"],
    "Small manufacturers": ["P05", "P21", "P24", "P08", "P16"],
}

# Products that require GSTIN (from spec)
GSTIN_REQUIRED_PRODUCTS = {"P03", "P05", "P06", "P10", "P12", "P13", "P14", "P15", "P21", "P24"}


class RulesEngine:
    def __init__(self, session: Session):
        self.session = session
        self.products: dict[str, Product] = {
            p.product_id: p for p in session.exec(select(Product)).all()
        }

    def infer_segment(self, profile: dict[str, Any]) -> str:
        btype = (profile.get("business_type") or "").lower()
        num_sites = int(profile.get("num_sites") or 1)
        if any(x in btype for x in ["clinic", "doctor", "ca", "chartered", "coaching", "law", "office", "consult", "advocate"]):
            return "Professional offices"
        if any(x in btype for x in ["factory", "manufact", "plant", "production", "industry"]):
            return "Small manufacturers"
        if num_sites >= 2:
            return "Small multi-site businesses"
        return "Micro retail & services"

    def is_eligible(self, pid: str, profile: dict[str, Any], bundle_ids: list[str]) -> tuple[bool, str]:
        p = self.products.get(pid)
        if not p:
            return False, "Unknown product"

        # City tier check
        tiers = [t.strip() for t in p.available_city_tiers.replace(";", ",").split(",")]
        if tiers and tiers != ["*"] and "*" not in tiers:
            city_tier = str(profile.get("city_tier") or "2")
            if city_tier not in tiers:
                return False, f"Available in Tier {', '.join(tiers)} cities only (you are in Tier {city_tier})"

        # Employee count check
        emp = int(profile.get("employee_count") or 0)
        if p.min_employees and emp < p.min_employees:
            return False, f"Needs {p.min_employees}+ employees (you have {emp})"

        # Sites check
        sites = int(profile.get("num_sites") or 1)
        if p.min_sites and sites < p.min_sites:
            return False, f"Needs {p.min_sites}+ sites (you have {sites})"

        # GSTIN check
        if p.requires_gstin == "Y" or pid in GSTIN_REQUIRED_PRODUCTS:
            if profile.get("has_gstin") != "Y":
                return False, "Needs GSTIN — here's how to get one: visit udyamregistration.gov.in or consult your CA"
            gst_status = profile.get("gst_status", "Active")
            if gst_status not in ("Active", ""):
                return False, f"GSTIN status is {gst_status} — please resolve before applying"

        # Dependency check (requires_one_of)
        if p.requires_one_of:
            required = [r.strip() for r in p.requires_one_of.split("|") if r.strip()]
            if required and not any(r in bundle_ids for r in required):
                return False, f"Requires one of these products in bundle: {', '.join(required)}"

        return True, ""

    def recommend_bundle(self, profile: dict[str, Any]) -> dict[str, Any]:
        segment = self.infer_segment(profile)
        template = SEGMENT_TEMPLATES.get(segment, SEGMENT_TEMPLATES["Micro retail & services"]).copy()
        bundle_ids = template.copy()

        # Mobile-only fast path
        if profile.get("mobile_only"):
            bundle_ids = ["P07", "P08"]
            if not profile.get("employee_count"):
                profile["employee_count"] = 1

        # Multi-site: add SD-WAN (P10) if 3+ sites, 10+ employees, GSTIN
        if int(profile.get("num_sites") or 1) >= 3 and int(profile.get("employee_count") or 0) >= 10 and profile.get("has_gstin") == "Y":
            if "P10" not in bundle_ids:
                bundle_ids.append("P10")

        # AirFiber vs Fibre: use P04 (AirFiber) if no current fibre
        # P02 is Biz Fibre, P04 is 5G AirFiber — both are eligible depending on tier
        # For Micro: prefer P04 (AirFiber) in Tier 1-2; keep P01/P02 for multi-site

        # Filter for user interests
        interests = profile.get("products_of_interest", [])
        if "cctv" in interests and "P23" not in bundle_ids:
            # P23 needs connectivity product already in bundle
            if any(p in bundle_ids for p in ["P01", "P02", "P04", "P05"]):
                bundle_ids.append("P23")
        if "billing_upi" in interests and "P19" not in bundle_ids:
            bundle_ids.append("P19")
        if "whatsapp_sms" in interests and "P13" not in bundle_ids:
            bundle_ids.append("P13")

        final = []
        excluded = []
        for pid in bundle_ids:
            ok, reason = self.is_eligible(pid, profile, final)
            if ok:
                final.append(pid)
            else:
                excluded.append({"product_id": pid, "reason": reason})

        # Build "why" list (reasons referencing owner's answers)
        why = self._build_why(segment, profile, final)

        return {
            "segment": segment,
            "bundle": final,
            "excluded": excluded,
            "bundle_name": self._bundle_name(segment),
            "why": why,
        }

    def _build_why(self, segment: str, profile: dict, bundle_ids: list) -> list:
        why = []
        btype = profile.get("business_type", "")
        emp = profile.get("employee_count", 0)
        sites = profile.get("num_sites", 1)

        if segment == "Professional offices":
            why.append(f"Built for {btype or 'professional'} businesses — secure email and backup included")
        elif segment == "Micro retail & services":
            why.append("Starter bundle for small businesses — affordable and all-in-one")
        elif segment == "Small multi-site businesses":
            why.append(f"One bill for all {sites} locations — includes failover so you never go offline")
        elif segment == "Small manufacturers":
            why.append("Industrial-grade connectivity + machine monitoring + managed security")

        if emp:
            why.append(f"Covers {emp} employees with shared mobile plans and email accounts")
        if profile.get("has_gstin") == "Y":
            why.append("GSTIN verified — eligible for advanced business services")
        elif profile.get("has_gstin") == "N":
            why.append("GST-free bundle — no GSTIN needed to get started")

        if profile.get("city_tier") == 1:
            why.append("Tier 1 city — full catalogue including 1 Gbps fibre available")

        return why[:4]

    def _bundle_name(self, segment: str) -> str:
        names = {
            "Micro retail & services": "Dukaan Digital",
            "Professional offices": "Clinic/Office Pro",
            "Small multi-site businesses": "One Bill",
            "Small manufacturers": "Plant Connect",
        }
        return names.get(segment, "Accel Business Bundle")

    def price_bundle(self, bundle_ids: list[str], contract_months: int = 24) -> dict[str, Any]:
        """
        Deterministic pricing:
        price = price_max - (price_max - price_min) * f
        f = clamp(0.5*(contract_months/24) + 0.1*(distinct_categories-1), 0, 1)
        """
        if not bundle_ids:
            return {
                "items": [],
                "monthly_total": 0,
                "one_time_total": 0,
                "gst": 0,
                "first_bill_estimate": 0,
                "bundle_saving": 0,
                "max_install_days": 0,
            }

        # Count distinct categories for bundle discount
        categories = set()
        for pid in bundle_ids:
            p = self.products.get(pid)
            if p:
                categories.add(p.category)
        distinct_cats = max(len(categories), 1)

        items = []
        monthly_total = 0.0
        one_time_total = 0.0
        max_install_days = 0

        for pid in bundle_ids:
            p = self.products.get(pid)
            if not p:
                continue
            c = max(contract_months, p.min_contract_months)
            f = min(max(0.5 * (c / 24.0) + 0.1 * (distinct_cats - 1), 0), 1.0)
            price_m = p.price_max - (p.price_max - p.price_min) * f
            price_m = round(price_m / 10) * 10  # round to nearest ₹10
            setup = p.one_time_setup
            install_days = p.typical_install_days

            items.append({
                "product_id": pid,
                "name": p.name,
                "category": p.category,
                "monthly": price_m,
                "setup": setup,
                "install_days": install_days,
                "min_contract_months": p.min_contract_months,
            })
            monthly_total += price_m
            one_time_total += setup
            max_install_days = max(max_install_days, install_days)

        # Saving = price at min contract vs current bundle price
        # For display: estimate 8% saving (conservative bundle discount)
        list_price = sum(
            (self.products[pid].price_max if pid in self.products else 0)
            for pid in bundle_ids
        )
        bundle_saving = max(0, round(list_price - monthly_total))

        gst = round(monthly_total * 0.18)

        return {
            "items": items,
            "monthly_total": round(monthly_total),
            "one_time_total": round(one_time_total),
            "gst": gst,
            "first_bill_estimate": round(monthly_total + gst + one_time_total),
            "bundle_saving": bundle_saving,
            "max_install_days": max_install_days,
            "contract_months": contract_months,
        }
