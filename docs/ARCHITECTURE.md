# Accel Business — Solution Architecture

## Overview
Project Udyam Digital employs a **Deterministic Core with LLM at the Edges** architecture. Business rules, product eligibility, dependency gating, and pricing arithmetic are handled strictly by a deterministic Python engine. AI is strictly leveraged for conversation slot-filling, plain-language explanations in 10 Indian languages, and document field extraction.

```mermaid
flowchart LR
    subgraph Client["Mobile-First PWA (390px)"]
        Owner["Business Owner (Web Speech / Touch)"]
        ReactApp["React 18 + Vite + Tailwind
shadcn/ui + Framer Motion"]
    end

    subgraph Gateway["FastAPI API Gateway"]
        AuthRouter["Router & CORS"]
        AuditLog["PII Masking & Audit Ledger"]
    end

    subgraph Edges["AI / OCR Layer (Edges)"]
        LLM["Anthropic Claude 3.5 Sonnet
(Vision & Tools)"]
        FallbackOCR["Local Deterministic Rules
+ Regex Extractor"]
    end

    subgraph Core["Deterministic Rules Core"]
        RulesEngine["Rules Engine
(City Tier, Min Emp/Sites, GSTIN)"]
        PricingEngine["Deterministic Pricing Engine
(Monotonic, Category Discounts)"]
        KYCValidator["KYC Engine (Checksum,
Age <= 90d, Fuzzy Name Match)"]
    end

    subgraph Services["Backend Services"]
        AdvisorSvc["Advisor Service"]
        OrderSvc["Order & Tracker Service"]
        OfficeSvc["Back-Office & Propensity Model
(Gradient Boosting Classifier)"]
    end

    subgraph Storage["Data & Registries"]
        SQLite[(SQLite DB: app.db
Seeded Catalogue & Leads)]
        ConsentLedger[(Append-Only Consent Ledger
DPDP Act 2023)]
        MockRegistries[("Mock GSTIN & Udyam Registries
(3,534 GSTIN / 2,723 Udyam)")]
    end

    Owner --> ReactApp
    ReactApp --> AuthRouter
    AuthRouter --> AuditLog

    AuditLog --> AdvisorSvc
    AdvisorSvc --> LLM
    AdvisorSvc -.-> FallbackOCR
    AdvisorSvc --> RulesEngine

    AuditLog --> KYCValidator
    KYCValidator --> MockRegistries
    KYCValidator --> ConsentLedger

    AuditLog --> OrderSvc
    OrderSvc --> SQLite

    AuditLog --> OfficeSvc
    OfficeSvc --> SQLite
    RulesEngine --> PricingEngine
```

## Trust Boundary & Data Flows
- **LLM Trust Boundary:** Identity numbers (GSTIN, Udyam, PAN, phone numbers) are masked or redacted before reaching external LLM calls. The advisor conversation only transmits anonymized business profile attributes (industry, staff count, branch count, city tier).
- **Data Minimisation:** Raw identity documents are uploaded only when registry lookup requires supplementary proof, and raw images are earmarked for deletion within 30 days per DPDP guidelines.
- **Append-Only Consent Ledger:** Every customer consent is hashed and permanently recorded with purpose, timestamp, and language.
