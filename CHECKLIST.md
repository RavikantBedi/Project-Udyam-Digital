# Project Udyam Digital — Build Checklist

- [x] **Phase 0: Data & Architecture Foundation**
  - [x] Inspect all synthetic data files (`product_catalogue.csv`, `smb_leads.csv`, registries, 47 KYC documents)
  - [x] Create clean project skeleton, Docker configuration, and database seed scripts
  - [x] Document empirical funnel insights and test matrices

- [x] **Phase 1: Deterministic Rules & Pricing Engine**
  - [x] Product eligibility (city tiers, min employees, min sites, GSTIN requirements, bundle dependencies)
  - [x] Monotonic pricing formula with category and contract duration discounts
  - [x] 100% test coverage with automated unit tests

- [x] **Phase 2: Conversational Advisor & Voice**
  - [x] Adaptive ≤ 6 question slot-filling flow with offline deterministic fallback
  - [x] Multi-lingual support (Hindi primary, English, Hinglish)
  - [ ] Web Speech API integration for microphone input (frontend — not yet implemented)
  - [x] Live recommendation card with "Why this fits you" rationales

- [x] **Phase 3: Transparent Quote & Checkout**
  - [x] Interactive contract duration toggle (12/24/36 months) with live pricing update
  - [x] First-bill estimate, 18% GST line, setup fees, and bundle saving display

- [x] **Phase 4: Smart KYC Pipeline**
  - [x] DPDP Act 2023 unbundled consent screen with append-only ledger
  - [x] GSTIN & Udyam format and checksum validation with mock registry auto-fetch
  - [x] Validation checklist with live Pass/Needs attention/Failed states
  - [x] Evaluated against test specimens K01–K12 (catching K01 expired bill defect)
  - [x] Simulated Aadhaar-OTP e-sign (demo OTP: 123456)

- [x] **Phase 5: Order Activation Tracker**
  - [x] Real-time milestone stepper with ETAs and SLA comparison chip (5d vs 17.6d)
  - [x] Simulated WhatsApp notification feed
  - [x] Interactive demo time-advance control

- [x] **Phase 6: Back-Office & Propensity Portal**
  - [x] Unclosed lead queue ranked by Gradient Boosting propensity model (0–100)
  - [x] Proxy discrimination safeguard (language and state excluded from features)
  - [x] Channel partner & field sales assignment with preserved commission attribution
  - [x] 5-metric target vs baseline dashboard and conversion funnel

- [x] **Phase U1: Backend Restructure (Production-grade)**
  - [x] Layered layout: app/api, app/schemas, app/services, app/repositories, app/security, app/llm, app/jobs, app/core
  - [x] Pydantic request/response schemas for every endpoint (no bare dict bodies)
  - [x] PostgreSQL via docker-compose (SQLite test override via DATABASE_TEST_URL)
  - [x] Alembic migrations (initial migration from current models)
  - [x] GSTIN/Udyam registries and catalogue in indexed tables (seeded once, idempotent)
  - [x] Removed per-request CSV scanning — repository layer for all DB access
  - [x] Single Settings class (pydantic-settings v2 ConfigDict), all values from env
  - [x] .env.example listing every variable
  - [x] DEMO_TODAY from settings only (removed hardcoded dates)
  - [x] Refuse to start in production if JWT_SECRET or APP_ENCRYPTION_KEY are default/empty
  - [x] HTTPException (400/401/403/404/409/422) instead of {"error": ...} with HTTP 200
  - [x] Global exception handler with consistent error shape and request ID
  - [x] Structured JSON logging with request IDs and PII-masking filter
  - [x] Health (/health) and readiness (/ready) endpoints
  - [x] CORS restricted to configured origins (no "*")
  - [x] Tooling: ruff clean, mypy basic, pytest with test database
  - [x] GitHub Actions workflow (lint, test, frontend build)
  - [x] 47 existing tests adapted and passing

- [x] **Phase U2: Real Authentication & Authorization**
  - [x] Argon2id password hashing with per-user salt
  - [x] Password policy: min length 10
  - [x] JWT access token (15 min) + rotating refresh token (7 days)
  - [x] Refresh tokens stored hashed in refresh_tokens table
  - [x] Tokens as httpOnly, Secure (prod), SameSite=Lax cookies — no localStorage
  - [x] CSRF protection (double-submit token header) for state-changing requests
  - [x] Endpoints: signup, signin, refresh, signout, signout-all, me, change-password, forgot/reset password
  - [x] Phone/email verification: OTP provider interface (Twilio Verify when configured, dev provider logs code)
  - [x] OTP: single-use, 5-minute expiry, max 5 attempts, stored hashed
  - [x] Rate limiting on signin, signup, OTP, advisor endpoints
  - [x] Account lockout with backoff after repeated failures
  - [x] Generic error messages (no user enumeration)
  - [x] get_current_user and require_role("owner","sales","partner","admin") on every non-public endpoint
  - [x] Public: health, catalogue, advisor (rate-limited, anonymous), lookups (rate-limited)
  - [x] Ownership checks: owner can only read/write own orders, consent, KYC, tracker; 404 for others' resources
  - [x] Seed roles from env: admin, sales, partner (dev only)
  - [x] Separate back-office data layer under /api/admin (own router, services, repositories)
  - [x] Roles: sales sees all leads; partner sees only assigned leads; admin manages users/LLM/model/audit
  - [x] Persist assignments: lead_assignments table with attribution tag, timestamps, outcome
  - [x] Immutable audit_log table (actor, role, action, resource, IP, timestamp, before/after hash)
  - [x] Audit: KYC record view, document download, export, assignment, login, settings change
  - [x] PII masking by role: partners see masked phone/GSTIN; unmasking requires sales/admin and is audited
  - [x] CSV export with same masking rules
  - [x] Tests: auth flow, token expiry/refresh rotation, replayed refresh token rejected, lockout, role matrix, ownership isolation, partner scoping, audit entries, masking

- [ ] **Phase U3: LLM Integration** (not started)
- [ ] **Phase U4: KYC Hardening** (not started)
- [ ] **Phase U5: Back-office & Metrics** (not started)
- [ ] **Phase U6: Frontend Upgrade** (not started)
- [ ] **Phase U7: Observability & Jobs** (not started)
- [ ] **Phase U8: Testing & CI** (not started)
- [ ] **Phase U9: Deployment Readiness** (not started)

**Known gaps (honest):**
- Frontend not yet upgraded to match new backend (no Zustand store, no shadcn/ui design system)
- Web Speech API not yet integrated
- LLM provider interface not yet wired (offline mode only)
- Model retraining is a stub (full implementation pending)
- Frontend TypeScript typecheck/Vite build not yet verified after backend changes
