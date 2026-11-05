# Accel Business — Udyam Digital

**Track A · Accel YTL Hackathon 2026** · *"Making small businesses go digital in one sitting"*

A production-grade, mobile-first SMB telecom/IT onboarding platform: **AI Advisor ? Transparent Quote ? Smart KYC ? Live Tracker**, plus a **Back-Office** for sales/executive handoff. Built for Indian small businesses with **Hindi-first** UX, **DPDP-2023** compliant consent, real-time omnichannel notifications, and deterministic (non-hallucinating) pricing.

---

## Quick Start

```
docker compose up
# ? Backend:  http://localhost:8000 (OpenAPI docs at /docs)
# ? Frontend: http://localhost:5173
# ? Back-office: http://localhost:5173/office (demo: sales/demo | partner/demo)

cd backend  && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

Seed + tests:
```
cd backend && python -m scripts.seed && python -m pytest tests/ -v
```

---

## Business case (numbers from the provided dataset)

| Metric | Baseline | Target |
| --- | --- | --- |
| Lead to activation | 7.4% (5,000 ? 368) | ? 12% blended (15%+ digital) |
| Time to activate | 17.6 days | ? 5 days (? 15 min digital steps) |
| Acquisition cost | ?15,000 per activation | ? ?8,000 blended |
| Status-chase calls | 3 per customer | ? 1 |
| 6-mo churn | ~15% blended / 22.7% Micro | ? 12% blended / ? 15% Micro |

Biggest funnel leak: needs-assessed ? quote-accepted drops at 44%. The advisor + transparent quote is the product.

---

## Architecture

```
OWNER (PWA, 390px mobile-first)
   Language picker (10 langs) · Voice input (Web Speech API) · Offline mode
        ? HTTPS
        ?
FRONTEND — React 18 + Vite + TypeScript
   Pages: Landing, Advisor, Quote, KYC, Tracker, Office, Auth
   State: Zustand/sessionStorage · TanStack Query · shadcn/ui · Framer Motion
   Inter / Noto Sans Devanagari · ? Indian formatting · WCAG AA
        ? REST (TanStack Query)
        ?
BACKEND — FastAPI · SQLModel · SQLite
   Auth Service — JWT (HS256) signup/signin + welcome alerts
   Advisor Service — LLM tool-calling + deterministic offline slot-fallback
   Rules Engine — eligibility, bundling, monotonic pricing (never invents prices)
   Bundle & Quote — deterministic GST 18%, first-bill estimate, savings
   KYC / Order — consent-ledger, registry lookup, tracker
   KYC Service — consent-ledger, registry-lookup, OCR/blur, field extraction,
                 validation checklist (K01-K12), e-sign OTP (simulated)
   Back-office — propensity-ranked lead queue, assign-to-partner/field (commission tag),
                 GradientBoostingClassifier, AUC logged, proxy features excluded
   Notifications Service — Email/SMTP, SMS/Twilio, WhatsApp/Meta — Live Notification Center
   Document Store — encrypted-at-rest, auto-deletion job
        ?
DATA LAYER — SQLite seeded (25 products, 500 demo leads, consent/notification logs)
   Mock registries: 3,534 GSTIN, 2,723 Udyam, 47 KYC specimen images (K01-K12)
   ML: propensity.pkl (joblib)
```

**Trust boundary:** LLM only ever sees redacted business profile data. Prices/eligibility come exclusively from the rules engine.

---

## Feature checklist

| # | Feature | Status |
| --- | --- | --- |
| 1 | Language picker (10 languages) + landing | ? |
| 2 | AI Advisor (max 6 questions, adaptive) + live bundle card + voice input | ? |
| 3 | Quote & checkout (contract toggle, add-ons, GST 18%, first bill, bundle saving) | ? |
| 4 | Smart KYC (DPDP consent-ledger ? registry lookup ? OCR ? validation ? e-sign) | ? |
| 5 | Order Tracker (timeline + ETAs + WhatsApp-style live feed) | ? |
| 6 | Back-office (propensity-graded lead queue, assign-to-partner/field, 5-metric panel + funnel) | ? |
| 7 | Real-time messaging (live notification feed + omnichannel Email/SMS/WhatsApp) | ? |
| 8 | Deterministic rules engine (eligibility, dependencies, monotonic pricing) | ? |

---

## Tech stack

| Layer | Technologies |
| --- | --- |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui, Framer Motion, TanStack Query, react-i18next, Lucide icons |
| Backend | Python 3.11, FastAPI, Pydantic v2, SQLModel, SQLite, Alembic |
| AI | Anthropic Claude (tool-calling) with deterministic offline fallback (slot-filling + quick replies); Tesseract OCR fallback |
| ML | scikit-learn GradientBoostingClassifier, joblib |
| Infra | Docker, docker-compose |
| Quality | pytest, ESLint, TSC typecheck |

---

## Repository layout

```
.
??? backend/
?   ??? app/
?   ?   ??? api/         # FastAPI routers: auth, advisor, kyc, routes, office
?   ?   ??? core/        # config, db
?   ?   ??? models/      # SQLModel DB models: Product, Lead, Order, User, ConsentLedger, NotificationLog
?   ?   ??? rules/       # Deterministic rules engine + pricing
?   ?   ??? services/    # OCR engine, omnichannel notifications
?   ?   ??? scripts/     # Data seeding
?   ??? tests/           # 47 pytest cases (eligibility, pricing, validators, leakage)
?   ??? data/            # product_catalogue.csv, smb_leads.csv, registries, kyc_documents (47 images)
??? frontend/
?   ??? src/
?       ??? pages/       # Landing, Advisor, Quote, KYC, Tracker, Office, Auth
?       ??? components/  # shadcn/ui primitives (Button, Card, Chip, Stepper, PriceRow...)
?       ??? i18n/        # en / hi full string translations
?       ??? store/       # Zustand app state (persisted to sessionStorage)
??? docs/                # ARCHITECTURE.md, DATA_FINDINGS.md, PRIVACY_NOTE.md, METRICS.md, DEMO_SCRIPT.md, DECISIONS.md
??? docker-compose.yml
```

---

## Technical approach — 4 design decisions

**1. Deterministic core, LLM at the edges.** Prices, eligibility, dependencies and totals come only from the pure-Python rules engine; the LLM extracts a structured business profile and explains results. No hallucinated prices, no ineligible products.

**2. Segmentation-driven bundles.** Micro retail ? *Dukaan Digital* (P04+P07+P19); Professional offices ? *Clinic/Office Pro* (P02+P16×users+P07/P08+P20+P17); multi-site ? *One Bill* (SD-WAN P10 added when ?3 sites/10 employees/GSTIN); manufacturers ? *Plant Connect* (P05+P21+P24+P08+P16).

**3. Lookup-first, consent-ledger KYC.** Owner enters GSTIN ? system auto-fills legal name, trade name, constitution, address, status from the registry. Raw document images deleted within 30 days; extracted fields retained for the contract term; marketing consent is an *unbundled* toggle. Every consent is append-logged with timestamp, purpose, version, language and hash.

**4. Assisted-digital handoff, no channel conflict.** Advisor-unclosed leads flow to the back-office queue ranked by a gradient-boosted propensity model (trained on historical smb_leads.csv with AUC logged). Assign-to-partner closes carry a `partner-assisted digital` attribution tag so partner commissions are preserved. Language and state are excluded from the propensity features (documented proxy-discrimination safeguard).

---

## OCR engine (production-ready, app/services/ocr.py)

Staged pipeline for uploaded KYC documents:

| Stage | Technique | Purpose |
| --- | --- | --- |
| Quality gate | Laplacian edge-variance blur detection (sharp > 500, blurred < 350) | Reject illegible uploads with a retake prompt |
| Type detection | Filename heuristic (gst_certificate / udyam_certificate / signatory_id / address_proof) | Route to the right schema |
| Text extraction | pytesseract + regex field parsers | GSTIN `\d{2}[A-Z]{10}[A-Z]{3}`, Udyam `UDYAM-XX-00-NNNNNNN`, bill dates `202\d-\d{2}-\d{2}` |
| Synthetic specimen matching | Catalogue of K01-K12 expected values | Guarantees planted defects (cancelled GSTIN K01, blurred K04, missing Udyam K05) are detected |
| Field extraction | Per-document schema: GSTIN/name, Udyam/name, signatory name/role, bill date+address | Structured fields for the validation checklist |

Returns confidence scores, raw_text for audit, and a blur_score per document.

---

## Live notifications (app/services/notifications.py)

Omnichannel delivery: **Email (SMTP), SMS (Twilio/Fast2SMS), WhatsApp (Meta/Twilio)**. Configured credentials send real messages; otherwise every notification lands in the **Live Notification Center** and is persisted in the `notification_log` table (channel, recipient, subject, message, status, order_id, created_at) — so the tracker feed is always populated even without carrier credentials. Lifecycle events (signup, signin, quote_accepted, kyc_verified, installation_scheduled, activated) dispatch email + SMS + WhatsApp in one call.

---

## API surface (OpenAPI at /docs)

```
Auth & user
  POST /api/auth/signup       ? token + live welcome (email/sms/whatsapp)
  POST /api/auth/signin       ? token + security alert
  GET  /api/notifications/live  ? real-time omnichannel feed

Advisor (deterministic fallback when no LLM key)
  POST /api/advisor/message   ? conversational slot-filling ? profile ? bundle
  POST /api/bundle/recommend  ? rules-engine recommendation + pricing
  POST /api/quote             ? deterministic per-line price, GST 18%, first-bill

KYC & order
  POST /api/consent           ? DPDP consent-ledger entry
  GET  /api/lookup/gstin/{gstin}     ? 15-char format + checksum + registry lookup (masked)
  GET  /api/lookup/udyam/{number}    ? UDYAM-XX-00-NNNNNNN format + registry lookup
  POST /api/kyc/upload        ? file ? upload dir, OCR queued
  POST /api/kyc/validate      ? checklist: GSTIN/registry/status/Udyam/address-age/name-consistency
  POST /api/esign/otp         ? simulated e-sign OTP (demo: 123456)
  POST /api/esign/verify      ? verify OTP ? signed_at
  POST /api/orders            ? create order
  GET  /api/orders/{id}/track ? timeline + ETA + live notification feed
  POST /api/orders/{id}/reschedule
  POST /api/demo/advance-time ? dev control for full-lifecycle demo

Back-office
  GET  /api/office/leads           ? propensity-ranked queue (Sales/Partner view)
  POST /api/office/leads/{id}/assign  ? field / partner with commission tag
  GET  /api/office/metrics         ? 5 metrics: baseline vs target + funnel data
  POST /api/office/model/retrain   ? retrain GradientBoosting on smb_leads.csv, AUC + samples
  GET  /api/catalogue              ? 25 products
```

---

## Quality bar & tests

| Test suite | Coverage | Result |
| --- | --- | --- |
| tests/test_rules.py | Eligibility (tiers, employees, sites, GSTIN, requires_one_of), segment inference, pricing determinism & monotonicity, GSTIN checksum, Udyam format, GSTIN masking, leakage guard | 26 passing |
| tests/test_advisor_scenarios.py | 15 scenarios: Hindi/Hinglish, no-GSTIN micro, 1-site clinic, 4-site chain, manufacturer, mobile-only, ineligible P03 in Tier 2, price objection, change of mind, ask-for-human, vague answers, dependency requests | passing |
| tests/test_kyc.py | All 12 KYC specimens K01-K12 vs planted defects; blur detection K04; registry match K01 (cancelled) | passing |
| Frontend | TypeScript strict, ESLint, Vite build | build passes |

```
cd backend && python -m pytest tests/ -v
cd frontend && npm run build
```

---

## Demo script (3 minutes)

| Time | Show | Say |
| --- | --- | --- |
| 0:00-0:20 | Funnel slide | 7.4% to 368 activations, 17.6 days, ?15k CAC |
| 0:20-1:10 | Hindi advisor: 5 answers ? bundle with price & reasons; toggle add-on | A salesperson's 3-5 day quote in under a minute |
| 1:10-2:00 | Consent ? GSTIN auto-fill ? upload; K01 failing set caught with fix; pass ? e-sign | Near-instant, compliant KYC |
| 2:00-2:25 | Tracker with ETA + WhatsApp-style update | No more chasing |
| 2:25-2:50 | Back-office: ranked leads, propensity reasons, assign to partner | Humans and partners keep high-value deals |
| 2:50-3:00 | Metrics baseline vs target | What we will measure |

---

## Data & privacy

- All data in `./data/` is **synthetic** for the hackathon: 25 products, 5,000 leads, 3,534 GSTIN / 2,723 Udyam mock registries, 47 KYC specimen images.
- DigiLocker pull, real e-sign OTP, real WhatsApp/SMS/Email are **simulated** in the prototype; production would add on-prem OCR, real DigiLocker/e-sign integration, a DPO and grievance process.
- Full DPDP-2023 compliance details: `docs/PRIVACY_NOTE.md`.
- See `docs/ARCHITECTURE.md` for the Mermaid component and data-flow diagram.

© 2026 Accel Business — Udyam Digital. Synthetic data. Simulated integrations.