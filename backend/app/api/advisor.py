"""Advisor router — conversational slot-filling with deterministic rules engine."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.schemas.schemas import (
    BundleRecommendReq,
    BundleRecommendResp,
    MessageReq,
    MessageResp,
)
from app.services.services import AdvisorService

router = APIRouter(prefix="/advisor", tags=["advisor"])


@router.post("/message", response_model=MessageResp)
def advisor_message(
    req: MessageReq,
    session: Session = Depends(get_session),
):
    service = AdvisorService(session)
    # Extract slots (keyword-based slot filling — deterministic fallback)
    profile = dict(req.profile)
    profile["lang"] = detect_language(req.message, profile.get("lang", ""))

    # Check for "talk to a person" intent
    lower = req.message.lower()
    if any(x in lower for x in ["talk to a person", "human", "agent", "kisi se baat", "help chahiye", "real person"]):
        return MessageResp(
            reply="Connecting you with a sales specialist. Your profile has been saved."
            if profile["lang"] == "hi"
            else "Connecting you with a sales specialist. Your profile has been saved.",
            profile=profile,
            recommendation=None,
            pricing=None,
            quick_replies=[],
            all_slots_filled=False,
            mode="offline",
            action="handoff",
        )

    result = service.recommend(profile)
    rec = result["recommendation"]
    pricing = result["pricing"]

    # Build why + next question
    why = []
    btype = profile.get("business_type", "")
    if btype:
        why.append(f"Tailored for {btype} businesses")
    emp = profile.get("employee_count", 0)
    if emp:
        why.append(f"Covers your team of {emp} employees")
    if profile.get("has_gstin") == "Y":
        why.append("Includes advanced services available with GSTIN")
    elif profile.get("has_gstin") == "N":
        why.append("GST-free bundle — no GSTIN required")
    rec["why"] = why

    next_q, quick_replies = next_question(profile, profile["lang"])
    all_slots_filled = not next_q

    reply = build_reply(rec, pricing, profile["lang"], next_q)

    return MessageResp(
        reply=reply,
        profile=profile,
        recommendation=rec if all_slots_filled else None,
        pricing=pricing if all_slots_filled else None,
        quick_replies=quick_replies,
        all_slots_filled=all_slots_filled,
        mode="offline",
    )


@router.post("/bundle/recommend", response_model=BundleRecommendResp)
def bundle_recommend(
    req: BundleRecommendReq,
    session: Session = Depends(get_session),
):
    service = AdvisorService(session)
    return service.recommend(req.profile)


def detect_language(text: str, profile_lang: str = "") -> str:
    import re
    if profile_lang in ("hi", "en"):
        return profile_lang
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    hinglish_words = ["mera", "meri", "hai", "hain", "nahi", "nahin", "aur", "kya", "kaise",
                      "chahiye", "dukaan", "ghar", "bhai", "sahab", "ji", "bhi"]
    lower = text.lower()
    if any(w in lower.split() for w in hinglish_words):
        return "hi"
    return "en"


def extract_slot(msg: str, profile: dict) -> dict:
    """Extract profile slots from user message."""
    lower = msg.lower()
    new_profile = profile.copy()

    # Business type
    if any(x in lower for x in ["clinic", "doctor", "hospital", "ca ", "chartered", "coaching", "law", "office", "consult", "advocate"]):
        new_profile["business_type"] = "Professional office"
    elif any(x in lower for x in ["factory", "manufact", "plant", "production", "industry"]):
        new_profile["business_type"] = "Manufacturing"
    elif any(x in lower for x in ["restaurant", "cafe", "dhaba", "hotel", "food"]):
        new_profile["business_type"] = "Restaurant"
    elif any(x in lower for x in ["shop", "retail", "dukaan", "store", "grocery", "medical store", "pharmacy"]):
        new_profile["business_type"] = "Retail Shop"

    # Employee count
    import re
    emp_patterns = [
        (r"(\d+)\s*(?:employee|staff|worker|log)", 1),
        (r"(?:employee|staff|worker|log)\s+(\d+)", 1),
    ]
    for pat, grp in emp_patterns:
        m = re.search(pat, lower)
        if m:
            new_profile["employee_count"] = int(m.group(grp))
            break
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)", lower)
    if m and "employee_count" not in new_profile:
        new_profile["employee_count"] = int(m.group(2))
    if "50+" in msg or "fifty" in lower:
        new_profile["employee_count"] = 50

    # Sites/branches
    m = re.search(r"(\d+)\s*(?:site|branch|location|outlet)", lower)
    if m:
        new_profile["num_sites"] = int(m.group(1))
    elif "single" in lower or "1 site" in lower or "one site" in lower:
        new_profile["num_sites"] = 1

    # City and tier
    CITY_TIER_MAP = {
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
    for city, tier in CITY_TIER_MAP.items():
        if city in lower:
            new_profile["city"] = city.title()
            new_profile["city_tier"] = tier
            break
    if "city_tier" not in new_profile and "city" not in new_profile:
        words = msg.split()
        for w in words:
            if w[0].isupper() and len(w) > 3:
                new_profile["city"] = w
                new_profile["city_tier"] = 2
                new_profile["city_tier_flag"] = "unknown_city_defaulted_tier2"
                break

    # GSTIN
    if any(x in lower for x in ["no gst", "without gst", "nahi gst", "gst nahi", "no gstin"]):
        new_profile["has_gstin"] = "N"
    elif any(x in lower for x in ["yes", "haan", "hai", "have gst", "gstin hai", "i have gst"]):
        if "gstin" in lower or "gst" in lower:
            new_profile["has_gstin"] = "Y"
    elif re.search(r"\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]", msg.upper()):
        new_profile["has_gstin"] = "Y"

    # Mobile-only intent
    if ("mobile" in lower or "phone" in lower or "sim" in lower) and ("only" in lower or "plan" in lower or "sirf" in lower):
        new_profile["mobile_only"] = True

    # What they want most
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
            interests = new_profile.get("products_of_interest", [])
            if want not in interests:
                interests.append(want)
            new_profile["products_of_interest"] = interests

    return new_profile


def next_question(profile: dict, lang: str = "en") -> tuple[str, list[str]]:
    """Return the next unanswered question and quick-reply options."""
    questions_hi = [
        "नमस्ते! आपका स्वागत है। आपका व्यवसाय किस प्रकार का है? (जैसे: दुकान, क्लिनिक, कारखाना, रेस्टोरेंट)",
        "आपके यहाँ कितने कर्मचारी हैं?",
        "आपकी कितनी शाखाएँ या साइट हैं?",
        "आप किस शहर में हैं?",
        "आप सबसे ज़्यादा क्या चाहते हैं? (इंटरनेट / WhatsApp-SMS / ईमेल-बैकअप / CCTV / बिलिंग-UPI / मोबाइल प्लान)",
        "क्या आपके पास GSTIN है?",
    ]
    questions_en = [
        "Welcome! What type of business do you have? (e.g. shop, clinic, factory, restaurant)",
        "How many employees do you have?",
        "How many branches or sites do you have?",
        "Which city are you in?",
        "What do you need most? (faster internet / WhatsApp & SMS / email & backup / CCTV / billing & UPI / mobile plans)",
        "Do you have a GSTIN?",
    ]
    quick_replies_map = {
        "business_type": ["Shop / Dukaan", "Clinic / Office", "Restaurant / Cafe", "Factory", "Coaching Centre"],
        "employees": ["1-5", "6-10", "11-25", "26-50", "50+"],
        "sites": ["1 (single)", "2-3", "4-10", "More than 10"],
        "wants": ["Faster Internet", "WhatsApp & SMS to customers", "Email & Backup", "CCTV Security", "Billing & UPI", "Mobile Plans"],
        "gstin": ["Yes, I have GSTIN", "No GSTIN yet", "Not sure"],
    }
    questions = questions_hi if lang == "hi" else questions_en
    if "business_type" not in profile:
        return questions[0], quick_replies_map["business_type"]
    if "employee_count" not in profile:
        return questions[1], quick_replies_map["employees"]
    if "num_sites" not in profile:
        return questions[2], quick_replies_map["sites"]
    if "city" not in profile:
        return questions[3], []
    if not profile.get("products_of_interest"):
        return questions[4], quick_replies_map["wants"]
    if "has_gstin" not in profile:
        return questions[5], quick_replies_map["gstin"]
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
