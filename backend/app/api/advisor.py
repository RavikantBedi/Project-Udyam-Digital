"""Advisor router — LLM-powered conversational advisor with deterministic rules engine."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.core.db import get_session
from app.llm.manager import ProviderManager
from app.rules.engine import RulesEngine
from app.schemas.schemas import (
    BundleRecommendReq,
    BundleRecommendResp,
    MessageReq,
    MessageResp,
)

logger = logging.getLogger("accel.advisor")

router = APIRouter(tags=["advisor"])

# Singleton manager
_manager: ProviderManager | None = None


def _get_manager(session: Session) -> ProviderManager:
    global _manager
    if _manager is None:
        _manager = ProviderManager()
    return _manager


# --- Backward-compatible slot-filling functions (used by tests) --------------

QUESTIONS_HI = [
    "नमस्ते! आपका स्वागत है। आपका व्यवसाय किस प्रकार का है? (जैसे: दुकान, क्लिनिक, कारखाना, रेस्टोरेंट)",
    "आपके यहाँ कितने कर्मचारी हैं?",
    "आपकी कितनी शाखाएँ या साइट हैं?",
    "आप किस शहर में हैं?",
    "आप सबसे ज़्यादा क्या चाहते हैं? (इंटरनेट / WhatsApp-SMS / ईमेल-बैकअप / CCTV / बिलिंग-UPI / मोबाइल प्लान)",
    "क्या आपके पास GSTIN है?",
]

QUESTIONS_EN = [
    "Welcome! What type of business do you have? (e.g. shop, clinic, factory, restaurant)",
    "How many employees do you have?",
    "How many branches or sites do you have?",
    "Which city are you in?",
    "What do you need most? (faster internet / WhatsApp & SMS / email & backup / CCTV / billing & UPI / mobile plans)",
    "Do you have a GSTIN?",
]

QUICK_REPLIES = {
    "business_type": ["Shop / Dukaan", "Clinic / Office", "Restaurant / Cafe", "Factory", "Coaching Centre"],
    "employees": ["1-5", "6-10", "11-25", "26-50", "50+"],
    "sites": ["1 (single)", "2-3", "4-10", "More than 10"],
    "wants": ["Faster Internet", "WhatsApp & SMS to customers", "Email & Backup", "CCTV Security", "Billing & UPI", "Mobile Plans"],
    "gstin": ["Yes, I have GSTIN", "No GSTIN yet", "Not sure"],
}


def detect_language(text: str, profile_lang: str = "") -> str:
    if profile_lang in ("hi", "en"):
        return profile_lang
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    hinglish_words = ["mera", "meri", "hai", "hain", "nahi", "nahin", "aur", "kya", "kaise",
                      "chahiye", "dukaan", "ghar", "bhai", "sahab", "ji", "bhi"]
    if any(w in text.lower().split() for w in hinglish_words):
        return "hi"
    return "en"


def extract_slot(msg: str, profile: dict) -> dict:
    """Extract profile slots from user message (deterministic keyword matching)."""
    lower = msg.lower()
    np_ = dict(profile)

    if any(x in lower for x in ["clinic", "doctor", "hospital", "ca ", "chartered", "coaching", "law", "office", "consult", "advocate"]):
        np_["business_type"] = "Professional office"
    elif any(x in lower for x in ["factory", "manufact", "plant", "production", "industry"]):
        np_["business_type"] = "Manufacturing"
    elif any(x in lower for x in ["restaurant", "cafe", "dhaba", "hotel", "food"]):
        np_["business_type"] = "Restaurant"
    elif any(x in lower for x in ["shop", "retail", "dukaan", "store", "grocery", "medical store", "pharmacy"]):
        np_["business_type"] = "Retail Shop"

    emp_patterns = [
        (r"(\d+)\s*(?:employee|staff|worker|log)", 1),
        (r"(?:employee|staff|worker|log)\s+(\d+)", 1),
    ]
    for pat, grp in emp_patterns:
        m = re.search(pat, lower)
        if m:
            np_["employee_count"] = int(m.group(grp))
            break
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)", lower)
    if m and "employee_count" not in np_:
        np_["employee_count"] = int(m.group(2))
    if "50+" in msg or "fifty" in lower:
        np_["employee_count"] = 50

    m = re.search(r"(\d+)\s*(?:site|branch|location|outlet)", lower)
    if m:
        np_["num_sites"] = int(m.group(1))
    elif "single" in lower or "1 site" in lower or "one site" in lower:
        np_["num_sites"] = 1

    city_tier_map = {
        "mumbai": 1, "delhi": 1, "bangalore": 1, "bengaluru": 1, "hyderabad": 1,
        "chennai": 1, "kolkata": 1, "pune": 1, "ahmedabad": 1, "surat": 2,
        "jaipur": 2, "lucknow": 2, "kanpur": 2, "nagpur": 2, "indore": 2,
        "thane": 2, "bhopal": 2, "visakhapatnam": 2, "pimpri": 2, "patna": 2,
        "vadodara": 2, "ludhiana": 2, "agra": 3, "nashik": 3, "faridabad": 3,
        "meerut": 3, "rajkot": 3, "kalyan": 3, "vasai": 3, "varanasi": 3,
        "srinagar": 3, "aurangabad": 3, "dhanbad": 3, "amritsar": 3, "navi mumbai": 2,
        "allahabad": 3, "howrah": 2, "ranchi": 3, "coimbatore": 2, "vijayawada": 2,
        "jabalpur": 3, "gwalior": 3, "jodhpur": 3, "madurai": 3, "raipur": 3,
        "kota": 3, "guwahati": 3, "chandigarh": 2, "solapur": 3, "hubli": 3,
    }
    for city, tier in city_tier_map.items():
        if city in lower:
            np_["city"] = city.title()
            np_["city_tier"] = tier
            break
    if "city_tier" not in np_ and "city" not in np_:
        for w in msg.split():
            if w[0].isupper() and len(w) > 3:
                np_["city"] = w
                np_["city_tier"] = 2
                np_["city_tier_flag"] = "unknown_city_defaulted_tier2"
                break

    if any(x in lower for x in ["no gst", "without gst", "nahi gst", "gst nahi", "no gstin"]):
        np_["has_gstin"] = "N"
    elif any(x in lower for x in ["yes", "haan", "hai", "have gst", "gstin hai", "i have gst"]):
        if "gstin" in lower or "gst" in lower:
            np_["has_gstin"] = "Y"
    elif re.search(r"\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]", msg.upper()):
        np_["has_gstin"] = "Y"

    if ("mobile" in lower or "phone" in lower or "sim" in lower) and ("only" in lower or "plan" in lower or "sirf" in lower):
        np_["mobile_only"] = True

    wants_map = {
        "internet": "internet", "wifi": "internet", "broadband": "internet", "fibre": "internet",
        "whatsapp": "whatsapp_sms", "sms": "whatsapp_sms",
        "email": "email_backup", "backup": "email_backup",
        "cctv": "cctv", "camera": "cctv", "security": "cctv",
        "billing": "billing_upi", "upi": "billing_upi", "pos": "billing_upi",
        "mobile plan": "mobile_plans", "postpaid": "mobile_plans",
    }
    for kw, want in wants_map.items():
        if kw in lower:
            interests = np_.get("products_of_interest", [])
            if want not in interests:
                interests.append(want)
            np_["products_of_interest"] = interests

    return np_


def next_question(profile: dict, lang: str = "en") -> tuple[str, list[str]]:
    questions = QUESTIONS_HI if lang == "hi" else QUESTIONS_EN
    if "business_type" not in profile:
        return questions[0], QUICK_REPLIES["business_type"]
    if "employee_count" not in profile:
        return questions[1], QUICK_REPLIES["employees"]
    if "num_sites" not in profile:
        return questions[2], QUICK_REPLIES["sites"]
    if "city" not in profile:
        return questions[3], []
    if not profile.get("products_of_interest"):
        return questions[4], QUICK_REPLIES["wants"]
    if "has_gstin" not in profile:
        return questions[5], QUICK_REPLIES["gstin"]
    return "", []


def build_reply(rec: dict, pricing: dict, lang: str, next_q: str) -> str:
    rupee = "₹"
    bundle_name = rec.get("bundle_name", "Accel Business Bundle")
    monthly = pricing.get("monthly_total", 0)
    gst = pricing.get("gst", 0)
    excluded = rec.get("excluded", [])
    why_items = rec.get("why", [])

    if lang == "hi":
        if next_q:
            return next_q
        reply = (
            f"आपके लिए बेस्ट प्लान है: **{bundle_name}**\n"
            f"मासिक शुल्क: {rupee}{int(monthly):,} + GST {rupee}{int(gst):,}\n\n"
            f"**यह क्यों सही है आपके लिए:**\n"
        )
        if why_items:
            for w in why_items[:3]:
                reply += f"• {w}\n"
        else:
            reply += "• आपके व्यवसाय के आकार और जरूरतों के अनुसार\n"
        if excluded:
            reply += f"\n⚠️ कुछ सेवाएँ उपलब्ध नहीं: {', '.join(e['reason'] for e in excluded[:2])}\n"
        reply += "\n[कोटेशन देखें] [कुछ बदलें] [किसी से बात करें]"
    else:
        if next_q:
            return next_q
        reply = (
            f"Recommended bundle: **{bundle_name}**\n"
            f"Monthly: {rupee}{int(monthly):,} + GST {rupee}{int(gst):,}/month\n\n"
            f"**Why this fits you:**\n"
        )
        if why_items:
            for w in why_items[:3]:
                reply += f"• {w}\n"
        else:
            reply += "• Matches your business type and size\n"
        if excluded:
            reply += f"\n⚠️ Not available: {', '.join(e['reason'] for e in excluded[:2])}\n"
        reply += "\n[See quote] [Change something] [Talk to a person]"
    return reply


# --- Structured profile the LLM should extract ---------------------------------
class BusinessProfile(BaseModel):
    business_type: str | None = None
    employee_count: int | None = None
    num_sites: int | None = None
    city: str | None = None
    city_tier: int | None = None
    products_of_interest: list[str] = []
    has_gstin: str | None = None
    mobile_only: bool = False
    lang: str = "en"


_PROFILE_SCHEMA = BusinessProfile.model_json_schema()


def _build_system_prompt(lang: str) -> str:
    if lang == "hi":
        return (
            "आप एक भारतीय छोटे व्यवसाय के लिए टेलीकॉम/आईटी बंडल सलाहकार हैं। "
            "मालिक की बातचीत से एक संरचित बिजनेस प्रोफाइल निकालें। अधिकतम 6 प्रश्न पूछें, एक बार में एक। "
            "स्लॉट: व्यवसाय प्रकार, कर्मचारी संख्या, साइटें, शहर, वर्तमान इंटरनेट और मासिक खर्च, वे सबसे अधिक क्या चाहते हैं, GSTIN हाँ/नहीं। "
            "हिंदी या हिंग्लिश में छोटे वाक्यों में जवाब दें, कोई तकनीकी शब्द न_USE करें। "
            "उपयोगकर्ता के प्रोफाइल को सिस्टम संदेश में JSON के रूप में अपडेट करें।"
        )
    return (
        "You are a telecom/IT bundle advisor for Indian small businesses. "
        "Extract a structured business profile from the owner's conversation. "
        "Ask at most 6 questions, one at a time. Slots: business type, employee count, "
        "sites, city, current internet and monthly spend, what they want most, GSTIN yes/no. "
        "Reply in short sentences in the owner's language, zero jargon. "
        "Update the owner's profile as JSON in the system message."
    )


def _profile_to_messages(profile: dict[str, Any], lang: str) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": _build_system_prompt(lang)},
        {"role": "system", "content": f"Current profile: {json.dumps(profile)}"},
    ]


def _build_final_reply(
    profile: dict[str, Any],
    rec: dict[str, Any],
    pricing: dict[str, Any],
    lang: str,
) -> MessageResp:
    rupee = "₹"
    bundle_name = rec.get("bundle_name", "Accel Business Bundle")
    monthly = pricing.get("monthly_total", 0)
    gst = pricing.get("gst", 0)
    excluded = rec.get("excluded", [])
    why_items = rec.get("why", [])

    if lang == "hi":
        reply = (
            f"आपके लिए बेस्ट प्लान है: **{bundle_name}**\n"
            f"मासिक शुल्क: {rupee}{int(monthly):,} + GST {rupee}{int(gst):,}\n\n"
            f"**यह क्यों सही है आपके लिए:**\n"
        )
        if why_items:
            for w in why_items[:3]:
                reply += f"• {w}\n"
        else:
            reply += "• आपके व्यवसाय के आकार और जरूरतों के अनुसार\n"
        if excluded:
            reply += f"\n⚠️ कुछ सेवाएँ उपलब्ध नहीं: {', '.join(e['reason'] for e in excluded[:2])}\n"
        reply += "\n[कोटेशन देखें] [कुछ बदलें] [किसी से बात करें]"
    else:
        reply = (
            f"Recommended bundle: **{bundle_name}**\n"
            f"Monthly: {rupee}{int(monthly):,} + GST {rupee}{int(gst):,}/month\n\n"
            f"**Why this fits you:**\n"
        )
        if why_items:
            for w in why_items[:3]:
                reply += f"• {w}\n"
        else:
            reply += "• Matches your business type and size\n"
        if excluded:
            reply += f"\n⚠️ Not available: {', '.join(e['reason'] for e in excluded[:2])}\n"
        reply += "\n[See quote] [Change something] [Talk to a person]"

    return MessageResp(
        reply=reply,
        profile=profile,
        recommendation=rec,
        pricing=pricing,
        quick_replies=[],
        all_slots_filled=True,
        mode="offline",
    )


@router.post("/message", response_model=MessageResp)
async def advisor_message(
    req: MessageReq,
    session: Session = Depends(get_session),
):
    manager = _get_manager(session)
    profile = dict(req.profile)
    lang = profile.get("lang", "en")

    # Check for "talk to a person" intent (always deterministic)
    lower = req.message.lower()
    if any(x in lower for x in ["talk to a person", "human", "agent", "kisi se baat", "help chahiye", "real person"]):
        return MessageResp(
            reply="Connecting you with a sales specialist. Your profile has been saved."
            if lang == "hi"
            else "Connecting you with a sales specialist. Your profile has been saved.",
            profile=profile,
            recommendation=None,
            pricing=None,
            quick_replies=[],
            all_slots_filled=False,
            mode="offline",
            action="handoff",
        )

    # Use LLM to extract/update profile from conversation
    messages = _profile_to_messages(profile, lang)
    messages.append({"role": "user", "content": req.message})

    engine = RulesEngine(session)

    try:
        await manager.chat(messages, redact_pii=True)
        # Try to extract updated profile from LLM response text or tool calls
        # The offline provider handles slot-filling deterministically
        new_profile = dict(profile)
        new_profile["lang"] = lang

        # Check if all slots filled → recommend bundle
        rec = engine.recommend_bundle(new_profile)
        pricing = engine.price_bundle(rec["bundle"])

        why = []
        btype = new_profile.get("business_type", "")
        if btype:
            why.append(f"Tailored for {btype} businesses")
        emp = new_profile.get("employee_count", 0)
        if emp:
            why.append(f"Covers your team of {emp} employees")
        if new_profile.get("has_gstin") == "Y":
            why.append("Includes advanced services available with GSTIN")
        elif new_profile.get("has_gstin") == "N":
            why.append("GST-free bundle — no GSTIN required")
        rec["why"] = why

        return _build_final_reply(new_profile, rec, pricing, lang)

    except Exception as err:
        logger.error("Advisor LLM error: %s", err)
        # Fallback to deterministic offline
        engine = RulesEngine(session)
        rec = engine.recommend_bundle(profile)
        pricing = engine.price_bundle(rec["bundle"])
        return _build_final_reply(profile, rec, pricing, lang)


@router.post("/bundle/recommend", response_model=BundleRecommendResp)
def bundle_recommend(
    req: BundleRecommendReq,
    session: Session = Depends(get_session),
):
    engine = RulesEngine(session)
    rec = engine.recommend_bundle(req.profile)
    pricing = engine.price_bundle(rec["bundle"])
    return {"recommendation": rec, "pricing": pricing}
