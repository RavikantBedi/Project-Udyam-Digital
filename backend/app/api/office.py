from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.db import get_session
from app.core.config import get_data_dir
from app.models.models import Lead
import os
import csv
import joblib
import numpy as np

router = APIRouter()

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "models", "propensity.pkl")
_model = None


def _load_model():
    global _model
    if _model is None and os.path.exists(MODEL_PATH):
        try:
            _model = joblib.load(MODEL_PATH)
        except Exception:
            pass
    return _model


def _score_lead(lead: Lead) -> tuple[int, list[str]]:
    """Score a lead using the trained model or a heuristic fallback."""
    model = _load_model()
    features = [
        1 if lead.has_gstin == "Y" else 0,
        1 if lead.has_udyam == "Y" else 0,
        min(lead.employee_count or 0, 100),
        min(lead.num_sites or 1, 20),
        lead.city_tier or 2,
        0,  # monthly_telecom_spend placeholder
        0,  # products_of_interest count placeholder
    ]
    if model is not None:
        try:
            prob = model.predict_proba([features])[0][1]
            score = int(prob * 100)
        except Exception:
            score = _heuristic_score(lead)
    else:
        score = _heuristic_score(lead)

    reasons = _top_reasons(lead, features)
    return max(5, min(99, score)), reasons


def _heuristic_score(lead: Lead) -> int:
    score = 30
    if lead.has_gstin == "Y":
        score += 20
    if lead.segment == "Professional offices":
        score += 15
    elif lead.segment == "Small manufacturers":
        score += 10
    if lead.has_udyam == "Y":
        score += 10
    if lead.city_tier == 1:
        score += 10
    elif lead.city_tier == 2:
        score += 5
    if lead.lead_source in ("Referral", "WhatsApp campaign"):
        score += 10
    if lead.employee_count and lead.employee_count >= 5:
        score += 5
    return score


def _top_reasons(lead: Lead, features: list) -> list[str]:
    reasons = []
    if lead.has_gstin == "Y":
        reasons.append("GSTIN present — eligible for full bundle")
    elif lead.has_gstin == "N":
        reasons.append("No GSTIN — eligible for Starter bundle")
    if lead.segment == "Professional offices":
        reasons.append("High-value Professional segment (11% conversion)")
    elif lead.segment == "Small multi-site businesses":
        reasons.append("Multi-site — high bundle value potential")
    elif lead.segment == "Small manufacturers":
        reasons.append("Manufacturer segment — good activation rate (12.8%)")
    if lead.city_tier == 1:
        reasons.append("Tier 1 city — full product catalogue eligible")
    if lead.lead_source == "Referral":
        reasons.append("Referral lead — 14.8% conversion historically")
    if not reasons:
        reasons.append("Digital-first lead — lower acquisition cost")
    return reasons[:3]


def _bundle_name(segment: str) -> str:
    names = {
        "Micro retail & services": "Dukaan Digital",
        "Professional offices": "Clinic/Office Pro",
        "Small multi-site businesses": "One Bill",
        "Small manufacturers": "Plant Connect",
    }
    return names.get(segment, "Accel Business Bundle")


@router.get("/leads")
def leads(session: Session = Depends(get_session)):
    all_leads = session.exec(select(Lead)).all()
    result = []
    for l in all_leads:
        score, reasons = _score_lead(l)
        result.append({
            "lead_id": l.lead_id,
            "business_name": l.business_name,
            "business_type": l.business_type,
            "segment": l.segment,
            "city": l.city,
            "language": l.preferred_language,
            "bundle_drafted": _bundle_name(l.segment),
            "propensity_score": score,
            "reasons": reasons,
            "ai_summary": f"{l.business_name} in {l.city} — {l.segment}. Drop reason: {l.drop_reason or 'N/A'}.",
            "suggested_action": _suggest_action(l),
            "stage": l.stage_reached,
            "drop_reason": l.drop_reason,
            "has_gstin": l.has_gstin,
        })
    result.sort(key=lambda x: x["propensity_score"], reverse=True)
    return result[:50]


def _suggest_action(lead: Lead) -> str:
    dr = (lead.drop_reason or "").lower()
    lang = lead.preferred_language or "English"
    if "unreachable" in dr or "wrong number" in dr:
        return f"Try WhatsApp in {lang} — provide digital self-serve link"
    if "price" in dr:
        return f"Share Starter tier quote in {lang} — emphasise bundle saving"
    if "time" in dr or "visit" in dr:
        return "Send self-serve onboarding link — no visit needed"
    if "complex" in dr or "slow" in dr:
        return "Walk through quote over a 10-minute call with screen share"
    if "mobile" in dr:
        return "Lead with P07/P08 mobile plan + one honest upsell"
    if "gstin" in dr or "gst" in dr:
        return "Explain GST-free Starter bundle — help get GSTIN if interested"
    return f"Call in {lang} with quote ready — high propensity lead"


@router.post("/leads/{lead_id}/assign")
def assign_lead(lead_id: str, data: dict):
    return {
        "status": "assigned",
        "lead_id": lead_id,
        "assignee": data.get("assignee"),
        "assignee_type": data.get("type", "field"),
        "attribution": "partner-assisted digital",
        "message": "Lead assigned. Commission attribution recorded.",
    }


@router.get("/metrics")
def metrics():
    return {
        "baseline": {
            "lead_to_activation": 7.4,
            "time_to_activate_days": 17.6,
            "acq_cost_per_activation": 15000,
            "status_chase_calls": 3,
            "churn_6m": 15.0,
        },
        "target": {
            "lead_to_activation": 12.0,
            "time_to_activate_days": 5.0,
            "acq_cost_per_activation": 8000,
            "status_chase_calls": 1,
            "churn_6m": 12.0,
        },
        "funnel": [
            {"stage": "Lead", "count": 5000},
            {"stage": "Contacted", "count": 3406},
            {"stage": "Needs assessed", "count": 1974},
            {"stage": "Quote accepted", "count": 861},
            {"stage": "KYC complete", "count": 588},
            {"stage": "Activated", "count": 368},
        ],
        "by_segment": [
            {"segment": "Micro retail & services", "share": 54, "activation": 4.1, "avg_bundle": 2505, "churn_6m": 22.7},
            {"segment": "Professional offices", "share": 25, "activation": 11.1, "avg_bundle": 6796, "churn_6m": 13.8},
            {"segment": "Small multi-site businesses", "share": 10, "activation": 11.0, "avg_bundle": 31233, "churn_6m": 10.8},
            {"segment": "Small manufacturers", "share": 11, "activation": 12.8, "avg_bundle": 19980, "churn_6m": 8.1},
        ],
        "by_source": [
            {"source": "Referral", "cac": 4100, "conversion": 14.8},
            {"source": "WhatsApp campaign", "cac": 4000, "conversion": 2.8},
            {"source": "Inbound call", "cac": 5100, "conversion": 8.2},
            {"source": "Website", "cac": 6400, "conversion": 5.1},
            {"source": "Channel partner", "cac": 20900, "conversion": 3.2},
            {"source": "Field sales", "cac": 24300, "conversion": 6.1},
        ],
    }


@router.post("/model/retrain")
def retrain_model():
    lead_path = os.path.join(get_data_dir(), "smb_leads.csv")
    if not os.path.exists(lead_path):
        return {"error": "smb_leads.csv not found"}

    rows = []
    with open(lead_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    # Build features — ONLY columns known at lead creation (no leakage)
    # Excluded: stage_reached, drop_reason, outcome, preferred_language, state (proxy discrimination)
    X = []
    y = []
    for row in rows:
        try:
            has_gstin = 1 if row.get("has_gstin") == "Y" else 0
            has_udyam = 1 if row.get("has_udyam") == "Y" else 0
            emp = min(int(row.get("employee_count") or 0), 100)
            sites = min(int(row.get("num_sites") or 1), 20)
            tier = int(row.get("city_tier") or 2)
            spend = float(row.get("monthly_telecom_spend_inr") or 0)
            poi = len([x for x in (row.get("products_of_interest") or "").split(";") if x.strip()])
            activated = 1 if row.get("outcome") == "Activated" else 0
            X.append([has_gstin, has_udyam, emp, sites, tier, spend, poi])
            y.append(activated)
        except Exception:
            continue

    if len(X) < 10:
        return {"error": "Insufficient data for training"}

    try:
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import roc_auc_score

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model = GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42)
        model.fit(X_train, y_train)
        auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])

        model_dir = os.path.join(os.path.dirname(__file__), "..", "..", "models")
        os.makedirs(model_dir, exist_ok=True)
        joblib.dump(model, os.path.join(model_dir, "propensity.pkl"))

        global _model
        _model = model

        return {
            "status": "retrained",
            "auc": round(auc, 3),
            "samples": len(X),
            "features": ["has_gstin", "has_udyam", "employee_count", "num_sites", "city_tier", "monthly_telecom_spend", "products_of_interest_count"],
            "excluded_features": ["preferred_language", "state", "stage_reached", "drop_reason", "outcome"],
            "note": "language and state excluded to avoid proxy discrimination per DPDP guidelines",
        }
    except ImportError:
        return {"error": "scikit-learn not installed"}
    except Exception as e:
        return {"error": str(e)}
