# Accel Business — Udyam Digital

**Track A · Accel YTL Hackathon 2026** · *"Making small businesses go digital in one sitting"*

A production-grade, mobile-first SMB telecom/IT onboarding platform: **AI Advisor ? Transparent Quote ? Smart KYC ? Live Tracker**, plus a **Back-Office** for sales/executive handoff. Built for Indian small businesses with **Hindi-first** UX, **DPDP-2023** compliant consent, real-time omnichannel notifications, and deterministic (non-hallucinating) pricing.

---

## ?? Quick Start

```bash
# Docker (recommended — includes PostgreSQL)
docker compose up
# ? Backend:  http://localhost:8000 (OpenAPI docs at /docs)
# ? Frontend: http://localhost:5173
# ? Back-office: http://localhost:5173/office

# Local development
cd backend  && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

### Seed database · Run tests
```bash
cd backend  && python -m scripts.seed
python -m pytest tests/ -v          # 47 tests passing
```

---

## ?? Business case (numbers from the provided dataset)

| Metric | Baseline | Target |
| --- | --- | --- |
| Lead ? activation | 7.4% (5,000 ? 368) | ? 12% blended (15%+ digital) |
| Time to activate | 17.6 days | ? 5 days (? 15 min digital steps) |
| Acquisition cost | ?15,000 per activation | ? ?8,000 blended |
| Status-chase calls | 3 per customer | ? 1 |
| 6-mo churn | ~15% blended / 22.7% Micro | ? 12% blended / ? 15% Micro |

Biggest funnel leak: needs-assessed ? quote-accepted drops at 44%. The advisor + transparent quote is the product.

---

## ??? Production architecture

```
OWNER (PWA, 390px mobile-first)
   Language picker (10 langs) · Voice input (Web Speech API — planned) · Offline mode
        ? HTTPS
        ?
FRONTEND — React 18 + Vite + TypeScript
   Pages: Landing, Advisor, Quote, KYC, Tracker, Office, Auth
   State: (Zustand store — planned) · TanStack Query · shadcn/ui (partial) · Framer Motion
   Inter / Noto Sans Devanagari · ? Indian formatting · WCAG AA
        ? REST (TanStack Query) + httpOnly cookies
        ?
BACKEND — FastAPI · SQLModel · PostgreSQL (dev: SQLite override)
   Auth Service — Argon2id passwords · JWT access (15m) + rotating refresh (7d) · httpOnly cookies
   Advisor Service — deterministic slot-filling (LLM integration planned)
   Rules Engine — eligibility · bundling · monotonic pricing (never invents prices)
   Bundle & Quote — deterministic GST 18% · first-bill estimate · savings
   KYC / Order — consent-ledger · registry lookup · tracker
   KYC Service — consent-ledger · registry-lookup · OCR/blur · field extraction
                 validation checklist (K01-K12) · e-sign OTP (simulated)
   Back-office — propensity-graded lead queue · assign-to-partner/field (commission tag)
                 GradientBoostingClassifier, AUC logged, proxy features excluded
   Notifications Service — Email/SMTP · SMS/Twilio · WhatsApp/Meta — Live Notification Center
   Document Store — (encryption at rest + auto-deletion job planned)
        ?
DATA LAYER — PostgreSQL (prod) / SQLite (tests)
   Alembic migrations · GSTIN registry (3,534) · Udyam registry (2,723) · 47 KYC specimen images
   ML: propensity.pkl (joblib)
```

**Trust boundary:** the LLM only ever sees redacted business profile data — no GSTIN, Udyam, phone or IDs cross the LLM boundary. Prices/eligibility come exclusively from the rules engine.

---

## ?? Feature checklist (honest status)

| # | Feature | Status |
| --- | --- | --- |
| 1 | Language picker (10 languages) + landing | ? |
| 2 | AI Advisor (max 6 questions, adaptive) + live bundle card | ? (deterministic, offline mode) |
| 3 | Voice input (Web Speech API) | ?? Planned — not yet implemented |
| 4 | Quote & checkout (contract toggle, add-ons, GST 18%, first bill, saving) | ? |
| 5 | Smart KYC (DPDP consent-ledger ? registry lookup ? OCR ? validation ? e-sign) | ? |
| 6 | Order Tracker (timeline + ETAs + WhatsApp-style live feed) | ? |
| 7 | Real-time messaging (live notification feed + omnichannel Email/SMS/WhatsApp) | ? (simulated in dev mode) |
| 8 | Deterministic rules engine (eligibility · dependencies · monotonic pricing) | ? |
| 9 | Real authentication (Argon2id, JWT access/refresh, httpOnly cookies, CSRF) | ? |
| 10 | Role-based access control (owner/sales/partner/admin) | ? |
| 11 | Back-office lead queue with propensity scoring | ? |
| 12 | Lead assignment persistence + audit log | ? |
| 13 | PII masking by role | ? |
| 14 | Real-time OTP verification (Twilio Verify or dev provider) | ? |

---

## ??? Tech stack

| Layer | Technologies |
| --- | --- |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui (partial), Framer Motion, TanStack Query, react-i18next, Lucide icons |
| Backend | Python 3.11, FastAPI, Pydantic v2, SQLModel, PostgreSQL/SQLite, Alembic |
| AI | Anthropic Claude (tool-calling — planned) with deterministic offline fallback; Tesseract OCR fallback |
| ML | scikit-learn GradientBoostingClassifier, joblib |
| Security | Argon2id, python-jose, passlib, CSRF double-submit, httpOnly cookies |
| Infra | Docker, docker-compose, PostgreSQL |
| Quality | ruff, pytest, GitHub Actions workflow |

---

## ?? Repository layout

```
.
??? backend/
?   ??? app/
?   ?   ??? api/         # FastAPI routers: auth, advisor, kyc, routes, office, admin
?   ?   ??? core/        # config, db
?   ?   ??? models/      # SQLModel DB models (User, Order, Lead, ConsentLedger, RefreshToken, OtpCode, ...)
?   ?   ??? rules/       # Deterministic rules engine + pricing
?   ?   ??? repositories/# All direct DB access (repositories)
?   ?   ??? services/    # Business logic use-cases (AuthService, AdminService, KYCService, OrderService, ...)
?   ?   ??? security/    # Argon2id, JWT, CSRF, current-user dependency
?   ?   ??? scripts/     # Data seeding
?   ?   ??? llm/         # LLM provider interface (planned)
?   ??? alembic/         # Database migrations
?   ??? tests/           # 47 pytest cases (eligibility, pricing, validators, leakage)
?   ??? data/            # product_catalogue.csv, smb_leads.csv, registries, kyc_documents (47 images)
??? frontend/
?   ??? src/
?       ??? pages/       # Landing, Advisor, Quote, KYC, Tracker, Office, Auth
?       ??? components/  # shadcn/ui primitives (partial)
?       ??? i18n/        # en / hi full string translations
?       ??? store/       # Zustand store (planned)
??? docs/                # ARCHITECTURE.md · DATA_FINDINGS.md · PRIVACY_NOTE.md · METRICS.md · DEMO_SCRIPT.md · DECISIONS.md
??? .github/workflows/   # CI: lint, test, frontend build
??? docker-compose.yml
??? README.md
```

---

## Technical approach — key decisions

**1. Deterministic core, LLM at the edges.** Prices, eligibility, dependencies and totals come only from the pure-Python rules engine; the LLM extracts a structured business profile and explains results. No hallucinated prices, no ineligible products.

**2. Segmentation-driven bundles.** Micro retail ? *Dukaan Digital* (P04+P07+P19); Professional offices ? *Clinic/Office Pro* (P02+P16×users+P07/P08+P20+P17); multi-site ? *One Bill* (SD-WAN P10 added when ?3 sites/10 employees/GSTIN); manufacturers ? *Plant Connect* (P05+P21+P24+P08+P16).

**3. Lookup-first, consent-ledger KYC.** Owner enters GSTIN ? system auto-fills legal name, trade name, constitution, address, status from the registry. Raw document images deleted within 30 days; extracted fields retained for the contract term; marketing consent is an *unbundled* toggle. Every consent is append-logged with timestamp, purpose, version, language and hash.

**4. Assisted-digital handoff, no channel conflict.** Advisor-unclosed leads flow to the back-office queue ranked by a gradient-boosted propensity model (trained on historical smb_leads.csv with AUC logged). Assign-to-partner closes carry a `partner-assisted digital` attribution tag so partner commissions are preserved. Language and state are excluded from the propensity features (documented proxy-discrimination safeguard).

**5. Defense-in-depth security.** Argon2id password hashing, JWT access (15 min) + rotating refresh (7 day) tokens stored hashed, httpOnly/Secure/SameSite cookies, CSRF double-submit protection, rate limiting, account lockout, PII masking by role, immutable audit log.

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

Omnichannel delivery: **Email (SMTP), SMS (Twilio/Fast2SMS), WhatsApp (Meta/Twilio)**. Configured credentials send real messages; otherwise every notification lands in the **Live Notification Center** and is persisted in the `notification_log` table — so the tracker feed is always populated even without carrier credentials. Lifecycle events (signup, signin, quote_accepted, kyc_verified, installation_scheduled, activated) dispatch email + SMS + WhatsApp in one call.

**Simulated in dev mode:** DigiLocker pull, real e-sign OTP, real WhatsApp/SMS/Email are simulated; production would add on-prem OCR, real DigiLocker/e-sign integration, a DPO and grievance process.

---

## API surface (OpenAPI at /docs)

```
Auth & user
  POST /api/auth/signup       ? token + live welcome (email/sms/whatsapp)
  POST /api/auth/signin       ? token + security alert
  POST /api/auth/refresh      ? rotate access + refresh tokens
  POST /api/auth/signout      ? revoke current refresh token
  POST /api/auth/signout-all  ? revoke all refresh tokens for user
  GET  /api/auth/me           ? current user profile
  POST /api/auth/change-password
  POST /api/auth/forgot-password   ? reset OTP via email
  POST /api/auth/reset-password
  POST /api/auth/otp/send     ? send OTP (dev mode logs code)
  POST /api/auth/otp/verify   ? verify OTP
  GET  /api/notifications/live  ? real-time omnichannel feed

Admin (roles: admin/sales/partner)
  GET  /api/admin/users           ? list users (admin only)
  POST /api/admin/users           ? create user (admin only)
  PATCH /api/admin/users/{id}/role ? update user role (admin only)
  GET  /api/admin/leads           ? role-scoped lead list
  POST /api/admin/leads/{id}/assign ? assign lead (admin/sales)
  PATCH /api/admin/assignments/{id}/outcome ? update outcome
  GET  /api/admin/audit-log       ? immutable audit log (admin only)
  GET  /api/admin/roles/matrix    ? role × endpoint access matrix

Advisor (rate-limited, anonymous allowed)
  POST /api/advisor/message   ? conversational slot-filling ? profile ? bundle
  POST /api/bundle/recommend  ? rules-engine recommendation + pricing

KYC & order
  POST /api/consent           ? DPDP consent-ledger entry
  GET  /api/lookup/gstin/{gstin}     ? format + checksum + registry lookup (masked)
  GET  /api/lookup/udyam/{number}    ? format + registry lookup
  POST /api/kyc/upload        ? file ? upload dir, OCR queued
  POST /api/kyc/validate      ? checklist: GSTIN/registry/status/Udyam/address-age/name-consistency
  POST /api/esign/otp         ? simulated e-sign OTP (demo: 123456)
  POST /api/esign/verify      ? verify OTP ? signed_at
  POST /api/orders            ? create order (owner only)
  GET  /api/orders/{id}/track ? timeline + ETA + live notification feed (owner only)
  POST /api/orders/{id}/reschedule
  POST /api/demo/advance-time ? dev control for full-lifecycle demo

Catalogue
  GET  /api/catalogue              ? 25 products

Meta
  GET  /health                     ? service health
  GET  /ready                      ? readiness probe (DB connectivity)
```

---

## Quality bar & tests

| Test suite | Coverage | Result |
| --- | --- | --- |
| tests/test_rules.py | Eligibility (tiers, employees, sites, GSTIN, requires_one_of), segment inference, pricing determinism & monotonicity, GSTIN checksum, Udyam format, GSTIN masking, leakage guard | 26 passing |
| tests/test_advisor_scenarios.py | 15 scenarios: Hindi/Hinglish, no-GSTIN micro, 1-site clinic, 4-site chain, manufacturer, mobile-only, ineligible P03 in Tier 2, price objection, change of mind, ask-for-human, vague answers, dependency requests | passing |
| tests/test_kyc.py | All 12 KYC specimens K01-K12 vs planted defects; blur detection K04; registry match K01 (cancelled) | passing |
| Ruff lint | All app/ source files | clean |
| Mypy | Basic type checking | partial |

```bash
cd backend && python -m pytest tests/ -v
cd backend && python -m ruff check app/
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
