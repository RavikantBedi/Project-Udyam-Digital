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
  - [x] Web Speech API integration for microphone input
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

- [x] **Phase 7: Testing & Quality Bar**
  - [x] 47/47 backend pytest test cases passing
  - [x] 15 custom advisor scenario tests passing
  - [x] Frontend TypeScript typecheck and Vite build passing with zero errors
