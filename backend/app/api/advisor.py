from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session
from app.core.db import get_session
from app.core.config import get_settings
from app.rules.engine import RulesEngine
import re

router = APIRouter()
settings = get_settings()

# --- CONVERSATION QUESTIONS (slot-filling flow) ---
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

# City-to-tier mapping from smb_leads data
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


def detect_language(text: str, profile_lang: str = "") -> str:
    if profile_lang in ("hi", "en"):
        return profile_lang
    # Detect Devanagari characters
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    # Hinglish detection (common Hindi words in Latin)
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
    emp_patterns = [
        (r"(\d+)\s*(?:employee|staff|worker|log)", 1),
        (r"(?:employee|staff|worker|log)\s+(\d+)", 1),
    ]
    for pat, grp in emp_patterns:
        m = re.search(pat, lower)
        if m:
            new_profile["employee_count"] = int(m.group(grp))
            break
    # Quick reply chips like "6-10" -> use upper bound
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
    for city, tier in CITY_TIER_MAP.items():
        if city in lower:
            new_profile["city"] = city.title()
            new_profile["city_tier"] = tier
            break
    if "city_tier" not in new_profile and "city" not in new_profile:
        # Try to extract any city-like word (capitalized)
        words = msg.split()
        for w in words:
            if w[0].isupper() and len(w) > 3:
                new_profile["city"] = w
                new_profile["city_tier"] = 2  # default to Tier 2 with flag
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
    return "", []  # All slots filled


def build_reply(rec: dict, pricing: dict, lang: str, next_q: str, quick_replies: list) -> str:
    """Build the advisor reply message."""
    rupee = "₹"
    bundle_name = rec.get("bundle_name", "Accel Business Bundle")
    monthly = pricing.get("monthly_total", 0)
    gst = pricing.get("gst", 0)
    excluded = rec.get("excluded", [])
    why_items = rec.get("why", [])

    if lang == "hi":
        if next_q:
            reply = f"{next_q}"
        else:
            reply = (
                f"आपके लिए बेस्ट प्लान है: **{bundle_name}**\n"
                f"मासिक शुल्क: {rupee}{int(monthly):,} + GST {rupee}{int(gst):,}\n\n"
                f"**यह क्यों सही है आपके लिए:**\n"
            )
            if why_items:
                for w in why_items[:3]:
                    reply += f"• {w}\n"
            else:
                reply += f"• आपके व्यवसाय के आकार और जरूरतों के अनुसार\n"
            if excluded:
                reply += f"\n⚠️ कुछ सेवाएँ उपलब्ध नहीं: {', '.join(e['reason'] for e in excluded[:2])}\n"
            reply += f"\n[कोटेशन देखें] [कुछ बदलें] [किसी से बात करें]"
    else:
        if next_q:
            reply = f"{next_q}"
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
                reply += f"• Matches your business type and size\n"
            if excluded:
                reply += f"\n⚠️ Not available: {', '.join(e['reason'] for e in excluded[:2])}\n"
            reply += f"\n[See quote] [Change something] [Talk to a person]"

    return reply


class MessageReq(BaseModel):
    message: str
    history: list = []
    profile: dict = {}


@router.post("/message")
async def advisor_message(req: MessageReq, session: Session = Depends(get_session)):
    lang = detect_language(req.message, req.profile.get("lang", ""))
    profile = extract_slot(req.message, req.profile)
    profile["lang"] = lang

    # Check for "talk to a person" intent
    lower = req.message.lower()
    if any(x in lower for x in ["talk to a person", "human", "agent", "kisi se baat", "help chahiye", "real person"]):
        return {
            "reply": "मैं आपको एक विशेषज्ञ से जोड़ रहा हूँ। कृपया प्रतीक्षा करें।\n\nConnecting you with a sales specialist. Your profile has been saved." if lang == "hi" else "Connecting you with a sales specialist. Your profile has been saved.",
            "profile": profile,
            "recommendation": None,
            "pricing": None,
            "mode": "offline",
            "action": "handoff",
        }

    engine = RulesEngine(session)
    rec = engine.recommend_bundle(profile)
    pricing = engine.price_bundle(rec["bundle"])

    # Add "why" reasons based on profile
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

    # Get next question (if slots not complete, ask next question)
    next_q, quick_replies = next_question(profile, lang)
    all_slots_filled = not next_q

    reply = build_reply(rec, pricing, lang, next_q, quick_replies)

    return {
        "reply": reply,
        "profile": profile,
        "recommendation": rec if all_slots_filled else None,
        "pricing": pricing if all_slots_filled else None,
        "quick_replies": quick_replies,
        "all_slots_filled": all_slots_filled,
        "mode": "ai" if settings.anthropic_api_key else "offline",
    }


@router.post("/bundle/recommend")
def bundle_recommend_advisor(profile: dict, session: Session = Depends(get_session)):
    engine = RulesEngine(session)
    rec = engine.recommend_bundle(profile)
    pricing = engine.price_bundle(rec["bundle"])
    return {"recommendation": rec, "pricing": pricing}
