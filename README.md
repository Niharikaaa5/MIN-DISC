# MIN-DISC: Task-Aware Minimum-Disclosure Planning for Privacy-Aware LLM Agents

## Project Objective
MIN-DISC is a final-year research project prototype designed to prevent over-disclosure of sensitive user profile attributes to external tools and APIs during LLM agent execution. Given a natural language user task, MIN-DISC extracts authoritative task requirements from official policy documents via Retrieval-Augmented Generation (RAG), identifies strictly necessary user attributes, creates an explainable minimum-disclosure plan, enforces deterministic policy rules, and discloses **only approved, task-justified attributes** to external tools.

The prototype supports two distinct, isolated workflows:
1. **Fresh Passport Application Workflow** (Adult, Ordinary Case, Citizen by Birth, Normal)
2. **PM-USP Central Sector Scheme of Scholarship (CSSS) Fresh Workflow** (College and University Students)

---

## Supported Workflows & Architectures

### 1. Fresh Passport Workflow
```text
USER TASK: "I want to apply for a fresh passport"
   │
   ▼
TASK-AWARE LLM AGENT / ORCHESTRATOR
   │
   ├── RAG RETRIEVAL ────────► Authoritative Passport PDFs (FAISS + Vector Store)
   │
   ├── REQUIREMENT EXTRACTION ─► Structured Task Requirements JSON
   │
   ├── ATTRIBUTE MATCHING ────► Explicit Mapping Rules:
   │                             • Proof of Present Address → address_proof (mandatory)
   │                             • Proof of Date of Birth → date_of_birth_proof (mandatory)
   │                             • Non-ECR Proof → academic_record (conditional)
   │
   ├── DISCLOSURE PLANNER ────► Approved Attributes Set (Task Necessity Only)
   │                             Excludes: phone, email, income, bank, medical, employment
   │
   └── POLICY CHECKER ────────► Deterministic Verification (ALLOW / BLOCK)
   │
   ▼
MOCK PASSPORT API (FastAPI / Receives MIN-DISC Approved Attributes Only)
```

---

### 2. PM-USP CSSS Fresh Scholarship Workflow
```text
USER TASK: "Apply for fresh PM-USP CSSS college scholarship"
   │
   ▼
SCHOLARSHIP BACKEND ORCHESTRATION PIPELINE
   │
   ├── ISOLATED RAG RETRIEVAL ─► data/requirements/scholarship/ (Guidelines, FAQ, NSP Manual)
   │                             Hierarchical Source Priority: Official Guidelines > FAQ > NSP Guide
   │
   ├── REQUIREMENT EXTRACTION ──► Structured Fresh CSSS Schema:
   │                             • Academic: 80th percentile cutoff, Board Top 20th list, No drop-year
   │                             • Income: Gross parental income <= Rs 4.5 Lakh p.a.
   │                             • Institutional: Regular full-time degree, recognized body, valid AISHE
   │                             • Supporting Docs: Class 12 mark sheet, Income cert, Caste/Disability cert
   │
   ├── ATTRIBUTE MATCHING ─────► 5-Way Evaluation:
   │                             1. Satisfied conditions
   │                             2. Failed substantive eligibility
   │                             3. Missing mandatory supporting documents
   │                             4. Missing conditional supporting documents
   │                             5. Quarantined payment credentials (DBT / PFMS)
   │
   ├── DISCLOSURE PLANNER ─────► Minimum-Disclosure Partition:
   │                             • portal_application_fields: Only required portal form inputs
   │                             • approved_supporting_documents: Strictly necessary documents only
   │                             • internal_eligibility_evaluation: Evaluated internally; never disclosed
   │                             • quarantined_payment_attributes: Raw Aadhaar, account, IFSC isolated
   │                             • excluded_attributes: Documented withheld attributes
   │
   ├── DETERMINISTIC POLICY ───► Policy Verification:
   │                             • PASSED: All requirements and documents satisfied
   │                             • BLOCKED: Substantive failure or missing mandatory document
   │                             • NEEDS_REVIEW: Missing critical verification data (e.g., missing AISHE code)
   │
   ├── HUMAN-IN-THE-LOOP GATE ─► Explicit User Approval Required (user_approved=True)
   │                             Unapproved plans pause at PENDING_USER_APPROVAL
   │
   ▼
MOCK NSP / PFMS API (FastAPI — Rejects Quarantined Credentials, Enforces Separate Payment Readiness)
```

---

## Technical Stack
- **Language**: Python 3.11+
- **RAG & Vector Store**: FAISS vector index (`faiss-cpu`), `pypdf` text extraction, `SentenceTransformers` / fitted `TF-IDF` vectorizer fallback
- **LLM API**: Google Gemini API (`google-genai`) with offline deterministic fallback
- **Mock Services**: FastAPI (`fastapi`, `uvicorn`, `starlette.testclient`)
- **Web UI**: Streamlit (`streamlit run app.py` — Passport interactive interface)

---

## Minimum-Disclosure & Privacy Enforcement

MIN-DISC enforces core privacy principles across all pipelines:
1. **Axiom of Minimum Disclosure**: *"Data availability must never be treated as data necessity."*
2. **Strict Payment Layer Quarantine**: Raw Aadhaar numbers, bank account numbers, IFSC codes, and Aadhaar seeding status are quarantined. They are never transmitted in application registration payloads.
3. **Cross-Workflow Isolation**: Passport-specific attributes (`passport_type`, `address_proof`, `date_of_birth_proof`) never enter scholarship payloads, and vice versa.
4. **Over-Disclosure Prevention**:
   - General category applicants are barred from attaching caste certificates.
   - Non-disabled applicants are barred from attaching disability certificates.
   - Any unapproved or unnecessary document triggers an immediate policy `BLOCKED` violation.
5. **Human-in-the-Loop Submission Gate**: Even if an application is fully eligible (`PASSED`), submission to external APIs cannot execute without explicit human confirmation (`user_approved=True`).

---

## Mock Scholarship API (NSP & PFMS Simulation)

The mock scholarship API (`src/scholarship/mock_scholarship_api.py`) simulates the National Scholarship Portal and PFMS gateway for prototype testing.

### Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health status and mock disclaimer. |
| `POST` | `/scholarship/apply` | Accepts policy-approved application payload; rejects quarantined payment data or extraneous attributes; generates synthetic `NSP-2025-CSSS-XXXXX` ID. |
| `GET` | `/scholarship/status/{id}` | Retrieves simulated application registration status (`SUBMITTED`, `UNDER_INSTITUTE_VERIFICATION`). |
| `GET` | `/scholarship/payment-status/{id}` | Independently evaluates simulated payment readiness (`PAYMENT_READY` vs `PAYMENT_PENDING`). |

### Decoupling Application Status vs Payment Readiness
In accordance with official CSSS operational guidelines (FAQ Q18):
- **Application Registration (`SUBMITTED`)**: An applicant studying in a recognized institution with an `INACTIVE` AISHE status is successfully registered on the portal.
- **Payment Disbursement (`PAYMENT_PENDING`)**: Payment release is independently placed on operational hold until the institution updates its status to `ACTIVE` on the AISHE portal.

### Mock API Disclaimer & Limitations
> [!IMPORTANT]
> - **Simulation Only**: The mock API is a local simulation for privacy research.
> - **No Government Calls**: The system **never** makes calls to actual NSP, PFMS, UIDAI (Aadhaar), Digilocker, or bank servers.
> - **No Guaranteed Award**: A `PASSED` policy check or `SUBMITTED` mock response does not represent an actual government scholarship grant.

---

## Setup & Installation

1. **Clone/Open Workspace**:
   Ensure you are in the project root directory `MIN-DISC`.

2. **Activate Virtual Environment**:
   ```powershell
   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Copy `.env.example` to `.env` and add your Gemini API key (optional for offline deterministic fallback):
   ```ini
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```

---

## Execution & Testing Guide

### 1. Run Scholarship Pipeline Benchmark (All 15 Synthetic Profiles)
```powershell
python src/scholarship/scholarship_pipeline.py --eval
```

### 2. Run Single Scholarship Applicant with Approval
```powershell
# Review plan without submitting (pauses at PENDING_USER_APPROVAL):
python src/scholarship/scholarship_pipeline.py SCH001

# Confirm explicit user approval and submit to Mock NSP:
python src/scholarship/scholarship_pipeline.py SCH001 --approve
```

### 3. Run Mock Scholarship API Unit Tests
```powershell
python tests/test_scholarship_api.py
```

### 4. Run Comprehensive Scholarship Integration Test Suite
```powershell
python tests/test_scholarship_pipeline.py
```

### 5. Run Passport Evaluation Benchmark (Zero Regressions)
```powershell
python src/main.py --eval
```

### 6. Launch Unified Streamlit Web Interface (Recommended for Demo / Viva)
```powershell
python -m streamlit run app.py
```
*Opens unified SaaS interface at `http://localhost:8501`. Features:*
- **🏠 System Dashboard**: Overview of minimum-disclosure architecture and two workflow cards.
- **🛂 Fresh Passport Workflow**: 4-stage pipeline for Adult Ordinary passport applications.
- **🎓 PM-USP CSSS Scholarship Workflow**: 8-stage pipeline for Fresh college scholarship applications (AY 2025–26) with decoupled payment readiness.
- **📊 Benchmark Tabs**: Empirical disclosure evaluation for Passport (U001-U010) and Scholarship (SCH001-SCH015).

---

## Evaluation Benchmark Results

### 1. Passport Workflow (10 Profiles)
- **Baseline Disclosures (Full Profile)**: 117 attributes
- **MIN-DISC Disclosures**: 16 attributes
- **Attributes Prevented from Leakage**: 101 attributes
- **Disclosure Reduction Ratio**: **86.3%**

### 2. PM-USP CSSS Scholarship Workflow (15 Synthetic Profiles)
| User ID | Applicant Name | Scenario Tested | Policy Status | Execution Outcome | Payment Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SCH001** | Aditya Sharma | Eligible General | `PASSED` | `SUBMITTED` | `PAYMENT_READY` |
| **SCH002** | Priya Patel | Family Income > Rs 4.5L Ceiling | `BLOCKED` | `BLOCKED` | N/A |
| **SCH003** | Naveen Kumar | Scored 82.5% marks, but Percentile 74.2 < 80th | `BLOCKED` | `BLOCKED` | N/A |
| **SCH004** | Sneha Kulkarni | Percentile 82.0, but Excluded from Board List | `BLOCKED` | `BLOCKED` | N/A |
| **SCH005** | Arjun Nair | Drop Year (AY 2025-26 scoped rule) | `BLOCKED` | `BLOCKED` | N/A |
| **SCH006** | Pooja Iyer | Missing Class 12 Mark Sheet (SD-01) | `BLOCKED` | `BLOCKED` | N/A |
| **SCH007** | Rahul Verma | Missing Income Certificate (SD-02) | `BLOCKED` | `BLOCKED` | N/A |
| **SCH008** | Meera Das | Eligible Reserved SC (Caste Cert attached) | `PASSED` | `SUBMITTED` | `PAYMENT_READY` |
| **SCH009** | Deepak Meena | Reserved ST, Missing Caste Certificate | `BLOCKED` | `BLOCKED` | N/A |
| **SCH010** | Siddharth Roy | Eligible PwD (Disability Cert attached) | `PASSED` | `SUBMITTED` | `PAYMENT_READY` |
| **SCH011** | Tanvi Deshmukh | Claimed PwD, Missing Disability Cert | `BLOCKED` | `BLOCKED` | N/A |
| **SCH012** | Karan Malhotra | Distance / Correspondence Education Mode | `BLOCKED` | `BLOCKED` | N/A |
| **SCH013** | Vikas Gowda | Pursuing Diploma (Degree only scheme) | `BLOCKED` | `BLOCKED` | N/A |
| **SCH014** | Anil Tiwari | Missing / Unverified AISHE Code | `NEEDS_REVIEW` | `NEEDS_REVIEW` | N/A |
| **SCH015** | Swati Sengupta | Concurrent Other Scholarship (Exclusivity) | `BLOCKED` | `BLOCKED` | N/A |

---

## Known Limitations & Scope
1. **Fresh Workflow Only**: The current scholarship prototype implements the Fresh Application workflow. Renewal processing is reserved for subsequent phases.
2. **Synthetic Data**: All applicant profiles (`data/users/scholarship_users.json` and `data/users/users.json`) contain completely synthetic data.
3. **Simulated Gateway**: Mock NSP and PFMS endpoints provide local validation for research testing only.
4. **Environment**: Vector index automatically falls back to fitted TF-IDF representation when Windows PyTorch native C++ libraries are unavailable.
