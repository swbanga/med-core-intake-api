# 🛡️ Med-Core Intake DevSecOps API

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Azure Container Apps](https://img.shields.io/badge/Deployed_on-Azure-0089D6?style=flat&logo=microsoft-azure&logoColor=white)](https://azure.microsoft.com/)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF?style=flat&logo=github-actions&logoColor=white)](https://github.com/swbanga/med-core-intake-api/actions)
[![Security](https://img.shields.io/badge/Security-Zero_Trust-red)](#)

An **enterprise‑grade, HIPAA‑aligned healthcare API** engineered with a strict **Zero‑Trust architecture**, cryptographic PHI protection, and a fully automated GitOps pipeline. This project demonstrates advanced DevSecOps principles, cloud‑native design, and rigorous security engineering—purpose‑built to withstand real‑world compliance audits.

---

## 🚀 Live Environment & Recruiter Access

Evaluate the system directly using the links and read‑only credentials below:

* **Live ReDoc Documentation:** [https://medcore-api.livelybush-d14e9c76.switzerlandnorth.azurecontainerapps.io/redoc](https://medcore-api.livelybush-d14e9c76.switzerlandnorth.azurecontainerapps.io/redoc)  
* **Interactive Swagger UI:** `/swagger` on the same host  
* **Postman Workspace:** [Med-Core DevSecOps Matrix](https://www.postman.com/superwbanga-7863188/workspace/med-core-devsecops-matrix)

> 🔐 **Auditor (Read‑Only) Credentials**  
> * **Email:** `demo@medcore.com`  
> * **Password:** `medcore-demo-2026`  
>  
> These credentials grant **view‑only** access to the entire patient vault—ideal for recruiters and evaluators.

---

## 🎯 Why Med‑Core Exists

Most healthcare CRUD examples ignore the **hardest 5%** of production engineering: encryption key rotation, token revocation, concurrency control, rate limiting, and immutable audit trails. **Med‑Core was built to solve those exact problems.**

It shows how to protect **Protected Health Information (PHI)** in a serverless cloud environment without sacrificing data integrity, availability, or developer velocity. The system follows the **12‑Factor App** methodology and enforces a **“fail‑closed”** security posture in every layer.

### Core Technology Stack

| Layer              | Technology                                                            |
|--------------------|-----------------------------------------------------------------------|
| **API Framework**  | Python 3.12, FastAPI (async)                                         |
| **Database**       | PostgreSQL 15, AsyncPG, SQLAlchemy 2.0 (Declarative Base)          |
| **Caching & Rate Limiting** | Redis 7 (Azure Cache for Redis)                              |
| **Encryption**     | Fernet (symmetric AES) with versioned key dictionary                |
| **Authentication** | OAuth2 / JWT with revocable JTI blacklist                           |
| **Infrastructure** | Azure Container Apps, Docker (GHCR)                                |
| **CI/CD Pipeline** | GitHub Actions (OIDC), Bandit SAST, pytest (async)                 |
| **IaC**            | Terraform (`medcore-prod-swiss-rg`)                                  |

---

## 🧠 Key Architectural Decisions & Hard‑Won Solutions

Every design choice addresses a real‑world threat. Below are the most impactful ones.

### 1. PHI Encryption with Zero‑Downtime Key Rotation
* **Problem:** A single hard‑coded encryption key means that a leak exposes all historical data, and rotating the key requires rewriting the entire database—often offline.
* **Solution:** All PHI fields (`first_name`, `last_name`, `medical_history`) are encrypted at the application layer with Fernet. Every ciphertext is prefixed with a version tag (e.g., `v1:encrypted_blob`). The system holds a dictionary of active keys (`ENCRYPTION_KEYS`). New data is encrypted with the current key, while old data can still be read using its original key—enabling seamless, zero‑downtime rotation.

### 2. Stripped‑Down JWTs & Fail‑Closed Token Revocation
* **Problem:** Storing a `role` inside a JWT creates a stale authorisation claim. A demotion won’t take effect until the token expires. Additionally, a Redis outage could crash the entire auth flow if not handled gracefully.
* **Solution:** JWTs contain **only** the user ID (`sub`) and token ID (`jti`). User roles are fetched from the database **on every request** (true zero‑trust). Token blacklisting via Redis is wrapped in `try/except`—if Redis is unavailable, the endpoint returns `503 Service Unavailable`, prioritising confidentiality over availability (fail‑closed).

### 3. Optimistic Concurrency Control (OCC)
* **Problem:** Two doctors updating the same patient profile simultaneously can cause a “lost update”—the second write silently overwrites the first.
* **Solution:** A `version` column is embedded in `PatientProfile`. Updates execute with `WHERE version = :expected_version` and atomically increment the version. If the version has changed since the client last read it, zero rows are affected and the server returns `409 Conflict`, preserving data integrity.

### 4. Immutable Audit Trail
Every profile modification is logged in `patient_profiles_history` **within the same database transaction**. This append‑only ledger captures the previous values and the actor’s ID, providing a verifiable, compliance‑grade audit record.

### 5. Invitation‑Based User Activation
* **Problem:** Having an admin set user passwords is insecure (the admin learns the password) and non‑compliant.
* **Solution:** Admins **invite** users by email and role name. A time‑limited, single‑use JWT is generated and delivered via a secure URL (email integration ready). The user sets their own password during activation—the admin never sees the plaintext secret, and the activation token is invalidated after first use.

### 6. Zero‑Trust CI/CD GitOps Pipeline
The pipeline is fully air‑gapped:
1. **Test stage** uses ephemeral Postgres/Redis containers—no production secrets are ever exposed.
2. On success, the CD stage:
   * Authenticates to Azure using OIDC (no static credentials).
   * Runs `alembic upgrade head` against the live production database.
   * Builds an immutable, multi‑stage Docker image (non‑root user).
   * Pushes to GitHub Container Registry and updates the Azure Container App.

### 7. Defense in Depth
* **Rate limiting** on every sensitive endpoint via Redis (login, patient CRUD, invitation, etc.).  
* **CORS** restricted to an environment‑defined list of origins.  
* **Structured JSON logging** with security telemetry for SIEM ingestion.

---

### 8. ⚙️ Local Development Setup

**Prerequisites:** Docker, Python 3.12, and a `.env` file (see `.env.example`).

1. **Clone the repository**
   ```bash
   git clone https://github.com/swbanga/med-core-intake-api.git
   cd med-core-intake-api

2. **Start the infrastructure**
    ```bash
    docker-compose -f docker-compose-dev.yml up -d

3. **Create a virtual environment & install dependencies**
    ```bash
    python -m venv venv
    source venv/bin/activate   # Windows: venv\Scripts\activate
    pip install -r requirements.txt

4. **Apply database migrations**
    alembic upgrade head

5. **Run the API**
    uvicorn app.main:app --reload --port 8000

6. **Open Swagger UI →** http://localhost:8000/swagger


### 9. Running the Test Suite
    All tests are async and run against a dedicated, per‑test database and Redis instance.

    ```bash 
    # pytest -v

    The suite covers:
    - Authentication & token lifecycle (issuance, revocation, expiry)
    - RBAC / ABAC (Patient, Doctor, Auditor, System_Admin)
    - Rate limiting (429 responses)
    - Invitation & activation flows
    - Optimistic concurrency conflicts (409)
    - IDOR (Insecure Direct Object Reference) prevention


###  🚢 Production Deployment

Deployment to **Azure Container Apps** is fully automated via `.github/workflows/ci.yml`. Every push to `main` triggers:

1. **Bandit SAST** scan  
2. **Pytest async suite** (ephemeral services)  
3. **Docker build & push** to GitHub Container Registry  
4. **Alembic migrations** against the live database  
5. **Container app update** with the new image and all env vars  

All secrets are stored in GitHub Secrets and injected at runtime. The Azure infrastructure is defined in Terraform (`terraform/main.tf`).

To deploy to your own subscription:

1. Fork the repository.  
2. Add the required secrets (see `.env.example`).  
3. Update the Terraform variables for your resource group and region.  
4. Run `terraform apply`.  
5. Push to `main`—the pipeline handles the rest.

---

## 📋 What Would I Improve Next?

- **Email Integration** – Swap the URL‑return activation for a transactional email service (SendGrid / Azure Communication Services).  
- **Centralised Key Management** – Integrate Azure Key Vault or HashiCorp Vault to manage encryption keys and rotate secrets dynamically.  
- **Observability** – Add Azure Application Insights for distributed tracing, custom metrics, and alerting.  
- **Performance** – Query caching for high‑frequency read endpoints (Redis).  
- **Advanced Deployment** – Canary releases using Azure Container Apps multiple revisions.

---

### 🤝 Why This Matters to a CTO

This project proves:

- **Security‑first mindset** – Encryption, token handling, concurrency control, and audit trails are baked in, not bolted on.  
- **Compliance readiness** – HIPAA‑aligned PHI encryption and immutable audit logs are foundational.  
- **Operational excellence** – Zero‑downtime deployments, automated migrations, and Infrastructure as Code mean a small team can manage the entire system.  
- **DevSecOps culture** – Testing, scanning, and deployment are unified in a single, repeatable pipeline—security is a continuous process, not a gate.

---

*Engineered by **Super Washington Banga*** | *Cloud Architect & DevSecOps Engineer*

