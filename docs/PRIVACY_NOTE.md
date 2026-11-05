# Data Privacy and Security Note (DPDP Act, 2023)

**Project:** Accel Business — Udyam Digital  
**Date:** 15 July 2026 (DEMO_TODAY)

### 1. Per-Purpose Consent Architecture
In strict alignment with Section 6 of the Digital Personal Data Protection (DPDP) Act 2023, consent is collected prior to touching any identity document.
- Plain-language notice in Hindi and English detailing the exact processing purpose (telecom KYC verification).
- Unbundled marketing consent: promotional communications use a separate, default-unchecked toggle that is never bundled with KYC consent.
- Verifiable Consent Ledger: Every consent event is recorded with an immutable SHA-256 hash, timestamp, purpose identifier, and language code.

### 2. Purpose Limitation & Data Minimisation
- **Lookup-First Verification:** Entering a GSTIN or Udyam number auto-populates registry verified records, avoiding redundant document uploads.
- **Redaction at LLM Boundary:** The AI Advisor never receives full GSTIN, PAN, or phone numbers. Only abstracted parameters (business category, headcount tier, city tier) are processed by LLM reasoning edges.
- No document is requested twice.

### 3. Data Retention & Erasure Schedule
- Raw uploaded document specimens (PNG/PDF) are purged after verification or within a 30-day statutory window.
- Extracted verification metadata is maintained under encrypted storage exclusively for the contract term.

### 4. Technical Safeguards & Masking
- **UI and Log Masking:** Identity numbers are systematically masked in logs and displays (e.g., `32TT••••••••1ZW`).
- **Role-Based Access Control:** Strict partitioning between business owner customer views and back-office sales/partner interfaces.

### 5. AI Risk & Determinism
- Pricing and eligibility calculations are 100% deterministic, eliminating LLM hallucinations in commercial quotations.
- A fully offline rules fallback guarantees continuous service during connectivity disruptions.
