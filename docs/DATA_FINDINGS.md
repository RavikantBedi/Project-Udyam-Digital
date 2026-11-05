# Project Udyam Digital — Data Findings from `smb_leads.csv`

Analysis of 5,000 synthetic SMB leads provides the empirical basis for our UX and rules architecture:

| Finding | Dataset Number | Design Consequence |
|---|---|---|
| **Biggest Funnel Leak** | Needs Assessed → Quote Accepted: **44% drop** | Transparent self-serve quote with zero hidden fees and instant bundle recommendation |
| **GSTIN Impact on Activation** | **9.6% with GSTIN** vs **2.0% without** (4.8x) | GSTIN lookup-first flow + distinct Starter bundle path for non-GSTIN micro shops |
| **Top Drop Reasons** | Unreachable after 3 attempts (805), No time for visit (531), Price too high (414), Quote too complex (206) | Self-serve digital onboarding eliminates scheduling visits and PDF turnaround delays |
| **Documentation Drops** | Missing GST/Udyam doc (94), Paperwork too long (79) | Auto-fetch from mock registry; ask for number first, fetch name and address |
| **Segment Economics** | Micro: 54% leads, 4.1% act., ₹2,505 avg; Professional: 25% leads, 11.1% act., ₹6,796 avg; Multi-site: ₹31,233 avg; Manufacturer: ₹19,980 avg | Digital-first for Professional offices; Low-touch starter for Micro; Assisted-digital for Multi-site & Manufacturers |
| **Source Economics (CAC)** | Referral ₹4.1k (14.8% conv), WhatsApp ₹4.0k, Inbound ₹5.1k, Channel partner ₹20.9k, Field sales ₹24.3k | Digital leads are 4–6x cheaper to acquire; human agents assigned to unclosed high-value leads with preserved commissions |
| **Status Chasing Impacts Retention** | Churn 5.9% at 1 follow-up call → 27.9% at 5 follow-up calls; NPS 7.5 → 6.0 | Live Order Tracker with WhatsApp feed eliminates chasing and protects 6-month retention |
| **Language Distribution** | Hindi 43%, English 23%, then Marathi, Gujarati, Tamil, Telugu, Kannada, Bengali, Punjabi, Malayalam | High-fidelity Hindi voice and text support alongside English |

## Synthetic Data Caveat
All statistics reflect synthetic distributions in the hackathon challenge dataset (`smb_leads.csv`).
