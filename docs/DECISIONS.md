# Architectural & Design Decisions

| ID | Decision | Context & Trade-off | Rationale |
|---|---|---|---|
| **DEC-01** | Deterministic Core + LLM at Edge | Risk of hallucinated telecom prices or ineligible bundles | Telecom tariffs are legally binding; LLM handles natural language while pure Python rules engine validates eligibility and pricing |
| **DEC-02** | Exclude Language & State from Propensity Model | Avoiding algorithmic proxy discrimination under DPDP guidelines | ML models can inadvertently penalize regional languages; scoring relies purely on objective business features (GSTIN, team size, sites, spend) |
| **DEC-03** | 2026-07-15 Fixed DEMO_TODAY Anchor | Synthetic dataset dates are anchored around July 2026 | Ensures deterministic 90-day KYC address-proof validation regardless of actual local execution time |
| **DEC-04** | Fast-path for Mobile-Only Intent | 280 drops in smb_leads.csv only wanted mobile plans | Rather than forcing full broadband bundles, offer P07/P08 with a clean digital upsell path |
| **DEC-05** | Portable Node.js & uv-managed Python 3.11 | Heterogeneous execution environments | Zero external dependency requirements; one-command bootstrap works cleanly |
