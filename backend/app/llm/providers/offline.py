"""Offline (deterministic) LLM provider — last-resort fallback.

Reuses the existing keyword-based slot-filling advisor logic so the demo
never dies when no LLM provider is configured or reachable.
"""
from __future__ import annotations

import re
from typing import Any

from app.llm.base import HealthCheckResult, LLMProvider, LLMResponse
from app.llm.circuit_breaker import CircuitBreaker, call_with_retry


class OfflineProvider(LLMProvider):
    name = "offline"
    timeout_seconds = 5
    max_retries = 0

    # --- deterministic slot-filling (same as advisor) ------------------
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

    def _detect_language(self, text: str, profile_lang: str = "") -> str:
        if profile_lang in ("hi", "en"):
            return profile_lang
        if re.search(r"[\u0900-\u097F]", text):
            return "hi"
        hinglish = ["mera", "meri", "hai", "hain", "nahi", "nahin", "aur", "kya", "kaise",
                    "chahiye", "dukaan", "ghar", "bhai", "sahab", "ji", "bhi"]
        if any(w in text.lower().split() for w in hinglish):
            return "hi"
        return "en"

    def _extract_slot(self, msg: str, profile: dict) -> dict:
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

    def _next_question(self, profile: dict, lang: str) -> tuple[str, list[str]]:
        questions = self.QUESTIONS_HI if lang == "hi" else self.QUESTIONS_EN
        quick_replies_map = {
            "business_type": ["Shop / Dukaan", "Clinic / Office", "Restaurant / Cafe", "Factory", "Coaching Centre"],
            "employees": ["1-5", "6-10", "11-25", "26-50", "50+"],
            "sites": ["1 (single)", "2-3", "4-10", "More than 10"],
            "wants": ["Faster Internet", "WhatsApp & SMS to customers", "Email & Backup", "CCTV Security", "Billing & UPI", "Mobile Plans"],
            "gstin": ["Yes, I have GSTIN", "No GSTIN yet", "Not sure"],
        }
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

    def _build_reply(self, rec: dict, pricing: dict, lang: str, next_q: str) -> str:
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

    # --- LLMProvider interface ----------------------------------------
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_schema: type[Any] | None = None,
        stream: bool = False,
    ) -> LLMResponse:
        import time as _t

        start = _t.monotonic()
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = m.get("content", "")
                break

        profile: dict[str, Any] = {}
        for m in messages:
            if m.get("role") == "system" and isinstance(m.get("content"), dict):
                profile = m["content"]

        lang = self._detect_language(user_msg, profile.get("lang", ""))
        profile = self._extract_slot(user_msg, profile)
        profile["lang"] = lang

        from sqlmodel import Session, SQLModel, create_engine

        from app.rules.engine import RulesEngine  # deferred import

        # Use in-memory engine for recommendations (no DB session needed here)
        test_engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(test_engine)
        # Minimal product seed so pricing works
        from app.models.models import Product
        with Session(test_engine) as s:
            s.add(Product(product_id="P04", name="5G AirFiber 100", category="Fibre/Fixed Wireless",
                          price_min=1499, price_max=1899, one_time_setup=500, min_contract_months=6,
                          available_city_tiers="1,2", min_employees=0, min_sites=1, requires_gstin="N",
                          requires_one_of="", typical_install_days=3, target_segments="Micro"))
            s.add(Product(product_id="P07", name="Business Postpaid 299", category="Mobile/Postpaid",
                          price_min=249, price_max=299, one_time_setup=0, min_contract_months=12,
                          available_city_tiers="1,2", min_employees=0, min_sites=1, requires_gstin="N",
                          requires_one_of="", typical_install_days=0, target_segments="Micro"))
            s.add(Product(product_id="P19", name="Cloud POS & Billing", category="SaaS/IT",
                          price_min=399, price_max=499, one_time_setup=0, min_contract_months=12,
                          available_city_tiers="1,2", min_employees=0, min_sites=1, requires_gstin="N",
                          requires_one_of="", typical_install_days=0, target_segments="Micro"))
            s.commit()
            engine = RulesEngine(s)
            rec = engine.recommend_bundle(profile)
            pricing = engine.price_bundle(rec["bundle"])

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

        next_q, quick_replies = self._next_question(profile, lang)
        reply = self._build_reply(rec, pricing, lang, next_q)

        return LLMResponse(
            text=reply,
            tool_calls=[],
            usage={},
            latency_ms=(_t.monotonic() - start) * 1000,
            provider=self.name,
            model="offline-slot-filling",
        )

    async def vision_extract(
        self,
        image_bytes: bytes,
        schema: dict[str, Any],
    ) -> LLMResponse:
        """Offline provider cannot do vision — returns a clear message."""
        import time as _t
        start = _t.monotonic()
        return LLMResponse(
            text="Vision extraction is not available in offline mode. Please configure Ollama or Anthropic provider.",
            tool_calls=[],
            usage={},
            latency_ms=(_t.monotonic() - start) * 1000,
            provider=self.name,
            model="offline",
        )

    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(
            healthy=True,
            latency_ms=0.0,
            error=None,
            provider=self.name,
            model="offline-slot-filling",
        )


# A shared circuit breaker for the offline provider (never opens)
_offline_breaker = CircuitBreaker(failure_threshold=999, recovery_timeout=60.0)


async def offline_chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    response_schema: type[Any] | None = None,
    stream: bool = False,
) -> LLMResponse:
    provider = OfflineProvider()
    return await call_with_retry(
        provider.chat, messages, tools=tools, response_schema=response_schema,
        stream=stream, max_retries=provider.max_retries,
        base_delay=0.5, max_delay=2.0, breaker=_offline_breaker,
    )
