# Lumen Cloud Deployment & Operations Guide

Production architecture, PostgreSQL configuration, Render blueprint deployment, and administrator console operations for Lumen.

---

## 1. Production Architecture Overview

Lumen is packaged as a single-service container hosting both the compiled React 18 SPA and the FastAPI Python 3.12 analytical server. Relational tenant metadata, user credentials, execution traces, and operational settings are persisted in PostgreSQL (Neon or Supabase), while high-throughput columnar analytics execute locally in embedded DuckDB instances.

```mermaid
flowchart TD
    subgraph Client["Client Browser"]
        UI["React 18 SPA (Vite + Tailwind)"]
        AdminUI["Admin Console (/admin2005)"]
    end

    subgraph Render["Render Free Tier Web Service"]
        FastAPI["FastAPI 0.115 Application (Uvicorn)"]
        Static["SPA Static Fallback Server"]
        Agent["PEVN Autonomous Agent Engine"]
        DuckDB["Tenant DuckDB Columnar Stores (/app/data)"]
    end

    subgraph Postgres["External Cloud PostgreSQL (Neon / Supabase)"]
        Users["users (auth & roles)"]
        Logs["admin_audit_logs & login_events"]
        Traces["execution_traces & cache_entries"]
        Settings["system_settings"]
    end

    subgraph LLMPool["LLM Inference Tier"]
        Groq["Groq Shared Pool (Llama 3.3 70B)"]
        Gemini["Google Gemini 2.0 Flash"]
        BYOK["User BYOK (Encrypted Credentials)"]
    end

    UI -->|HTTPS / WSS| FastAPI
    AdminUI -->|REST Bearer Token| FastAPI
    FastAPI --> Static
    FastAPI --> Agent
    Agent -->|Columnar Analytics| DuckDB
    FastAPI -->|psycopg 3 Connection Pool| Postgres
    Agent -->|Raw REST HTTPX| LLMPool
```

---

## 2. PostgreSQL Setup (Neon / Supabase)

Lumen supports dual database engines: local SQLite for development and PostgreSQL (version 15+) for production.

### Neon Setup
1. Sign up at [neon.tech](https://neon.tech) and create a new project (e.g. `lumen-prod`).
2. In the Neon dashboard, navigate to **Dashboard** and copy the connection string.
3. Select **Connection Pooling** mode if available (PgBouncer transaction mode).
4. Example Neon connection string:
   ```text
   postgres://username:password@ep-cool-service-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

### Supabase Setup
1. Sign up at [supabase.com](https://supabase.com) and create a new project.
2. Navigate to **Project Settings > Database > Connection string**.
3. Select the **URI** tab. Use the pooled connection string (port `6543`) for transaction pooling, or port `5432` for direct connection.
4. Ensure `sslmode=require` is present in the URI.

### Driver Normalization & Pooler Hardening
Lumen automatically normalizes legacy URI schemes:
- `postgres://` and `postgresql://` are converted to `postgresql+psycopg://` so SQLAlchemy 2 uses the modern `psycopg` v3 driver.
- Non-local hostnames automatically append `sslmode=require` if not specified.
- To prevent transaction pooler prepared-statement collision (common with PgBouncer, Neon poolers, and Supabase transaction poolers), Lumen configures:
  ```python
  connect_args={"prepare_threshold": None}
  ```
- Startup connection retries: Lumen attempts up to 5 connection retries with exponential backoff before failing, preventing container crashes during slow database wake-ups.
- Advisory lock migration guard: on boot, Alembic migrations run under PostgreSQL advisory lock `84729104` to eliminate race conditions across multiple instances.

---

## 3. Render Blueprint Deployment

Lumen includes a production-ready `render.yaml` blueprint configured for Render's free tier.

### Step-by-Step Deployment
1. Push your repository to GitHub.
2. Log in to [render.com](https://render.com).
3. In the Render Dashboard, click **New +** and select **Blueprint**.
4. Select your GitHub repository: `vijaykasthurik/INTERN-DBO-SDE-VIJAY-KASTHURI`.
5. Render detects `render.yaml` and displays the service definition:
   - **Service Name**: `lumen`
   - **Environment**: `Docker`
   - **Plan**: `Free`
   - **Region**: `Oregon`
   - **Health Check Path**: `/health`
6. Fill in the required environment variables (see category breakdown below).
7. Click **Apply Blueprint**. Render builds the multi-stage Docker image and deploys.

### Environment Variable Categorization

The environment variables required for Render deployment are categorized into three distinct classes:

#### Category A: Secret Variables (Set manually in Render Dashboard as sensitive)
| Variable Name | Description | Required | Example Format |
|---|---|---|---|
| `DATABASE_URL` | Cloud PostgreSQL connection string (Neon / Supabase) | Yes | `postgres://user:pass@ep-cool.neon.tech/neondb` |
| `ADMIN_EMAIL` | Initial administrator login email | Yes | `ops@yourcompany.com` |
| `ADMIN_PASSWORD` | Administrator password (minimum 14 characters) | Yes | `ProductionAdminPassword2026!#` |
| `ADMIN_TOTP_SECRET` | Optional RFC 6238 Base32 secret for 2FA TOTP | Optional | `JBSWY3DPEHPK3PXP` |
| `GROQ_API_KEY` | Primary Groq API key for inference | Yes | `gsk_...` |
| `GROQ_API_KEY_1` .. `7` | Additional pool keys for round-robin rotation | Optional | `gsk_...` |
| `GEMINI_API_KEY` | Fallback Gemini API key | Optional | `AIzaSy...` |
| `OPENROUTER_API_KEY` | Fallback OpenRouter API key | Optional | `sk-or-v1-...` |
| `ZAI_API_KEY` | Fallback Z.AI API key | Optional | `sk-...` |
| `HF_API_KEY` | Hugging Face serverless inference token | Optional | `hf_...` |
| `DEEPSEEK_API_KEY` | Fallback DeepSeek API key | Optional | `sk-...` |

#### Category B: Fixed in render.yaml (Automatically populated by Blueprint)
| Variable Name | Value in render.yaml | Purpose |
|---|---|---|
| `APP_ENV` | `production` | Enforces production mode and disables mock LLM |
| `PORT` | `10000` | Render internal HTTP routing port |
| `DATA_DIR` | `/app/data` | Container path for DuckDB tenant databases |
| `WEB_CONCURRENCY` | `1` | Restricts worker count to prevent multi-process RAM multiplication |
| `MALLOC_ARENA_MAX` | `2` | Limits glibc memory arena fragmentation |
| `LLM_PROVIDER` | `groq` | Primary LLM inference engine |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Strong-tier reasoning model identifier |
| `ADMIN_RESET` | `false` | Prevents re-seeding admin password on every boot |

#### Category C: Render-Generated (Cryptographically created by Render on deploy)
| Variable Name | Generation Directive | Purpose |
|---|---|---|
| `SECRET_KEY` | `generateCrypto: true` | HMAC signing secret for session JWT tokens (>= 32 chars) |
| `KEY_ENCRYPTION_SECRET` | `generateCrypto: true` | AES-256-GCM secret for BYOK user keys (>= 32 chars) |

---

## 4. Administrator Console (`/admin2005`)

Lumen provides a dedicated, high-density operations console designed for administrators.

### Access & Security Hardening
- **Route**: `https://<your-render-url>/admin2005`
- **Security & Discoverability**: The route is completely hidden from public navigation, navbar, sitemaps, and search engines.
- **Headers**: All administrative endpoints and the route return `X-Robots-Tag: noindex, nofollow`.
- **Audience & Token Scoping**: Administrative JWTs have audience `aud='admin'`, role `role='admin'`, and a 30-minute expiry. Regular user tokens receive `403 Forbidden`.
- **Lockout Protection**: 5 consecutive failed login attempts from any IP trigger a 15-minute rate-limit lockout (`429 TOO_MANY_REQUESTS`).
- **Zero Secret Exposure**:
  - The "Reveal" toggle and endpoint have been permanently removed.
  - Sensitive columns (`hashed_password`, `ciphertext`, `admin_totp_secret`, `secret_key`, etc.) are completely omitted from table schema metadata, table browsing, SQL query responses, and CSV exports.
  - The runtime configuration view displays environment variable NAMES and boolean `is_set` status (`SET` / `NOT SET`) ONLY; environment values and keys are never returned.
- **Admin Password Seeding**:
  - On application startup, `seed_admin_user` checks if the admin account already exists.
  - If existing, the password hash is **never** reset or overwritten on boot.
  - Password updates occur **only** when `ADMIN_RESET=true` is explicitly configured.

### Configuring 2FA TOTP (Optional)
To require two-factor authentication for the admin console:
1. Generate an RFC 6238 Base32 secret using Python:
   ```bash
   python -c "import pyotp; print(pyotp.random_base32())"
   ```
2. Set the `ADMIN_TOTP_SECRET` environment variable in Render.
3. Import the secret into Google Authenticator or 1Password using the secret key or URI:
   ```text
   otpauth://totp/Lumen%20Admin:ops@company.com?secret=YOUR_SECRET&issuer=Lumen
   ```
4. Subsequent logins will require the current 6-digit TOTP code.

### Console Features by Tab

#### Tab 1: System Dashboard
- **Real-Time Telemetry**: Active users (last 24 hours, 7 days, 30 days), total datasets hosted, queries executed, tokens processed, and estimated cost ($ USD).
- **LLM Provider Health Grid**: Live status (UP / DEGRADED / DOWN), latency in milliseconds, and circuit breaker states for all configured model providers.
- **Volume & Token Charts**: Interactive Apache ECharts visualizing daily queries over the past 30 days and token consumption by provider.
- **Authentication Log**: Inspection table of the last 50 login attempts across the platform with IP address, role, timestamp, and failure reasons.

#### Tab 2: User Management
- **Directory**: Paginated list of registered users with email search, role filters, and sorting.
- **Resource Utilization**: Datasets count, agent query count, and DuckDB disk storage in megabytes.
- **Inspect Details**: Modal inspection of a user's uploaded datasets and recent chat sessions.
- **Account Actions**:
  - **Enable / Disable**: Deactivates accounts and immediately increments `token_version` to invalidate existing JWT tokens.
  - **Force Logout**: Increments `token_version` without disabling the account, forcing re-authentication.
  - **Delete User**: Permanent cascade deletion removing all user rows, DuckDB tables, and uploaded CSV files.

#### Tab 3: Database & SQL Console
- **Table Browser**: Schema viewer and paginated data grid for all metadata tables. Sensitive credential columns are omitted.
- **SQL Console (Read-Only)**:
  - Single-statement `SELECT` runner parsed and validated via `sqlglot` AST traversal.
  - Strict rejection of all mutation expressions (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`).
  - Hard limit of 500 rows and 5-second statement timeout.
  - **Export CSV**: One-click download of query results to a CSV file (free of sensitive credentials).
- **Maintenance**:
  - **Run Vacuum & Analyze**: Reclaims free pages and updates statistics (`VACUUM ANALYZE` on Postgres, `VACUUM` on SQLite).
  - **Purge Old Traces**: Purges execution logs older than 30 days.
  - **Clear Cache**: Flushes verified-answer cache entries.

#### Tab 4: Operations & Settings
- **Dynamic Feature Flags**:
  - *Allow Public Registration*: Toggle new account creation.
  - *Smart Provider Fallback*: Toggle shared pool fallback when user BYOK keys fail.
  - *Global Maintenance Mode*: Displays maintenance banner to non-admin users.
- **Runtime Environment View**: Clean grid displaying variable names and `SET` / `NOT SET` badges only. No values or secrets are leaked.
- **Contact Messages Inbox**: View submissions from the public Contact form, reply via email client (`mailto:`), or delete.

#### Tab 5: Audit Log
- **Immutable Log**: Filterable record of administrative actions (`admin.login`, `user.delete`, `sql.query`, `setting.update`, `maintenance`).
- **Audit Detail Expander**: Collapsible JSON inspector showing contextual parameters and client IP addresses.

### Emergency Password Reset
If locked out of the admin console:
1. In the Render Dashboard, set `ADMIN_RESET=true` and update `ADMIN_PASSWORD` with a new password (min 14 chars).
2. Redeploy the service.
3. On startup, Lumen updates the admin hash with the new password and logs the reset event.
4. Set `ADMIN_RESET=false` after logging in.

---

## 5. Measured Memory Usage & Free-Tier Verification

Render's free tier provides 512 MB of RAM. Lumen has been benchmarked using `docker stats` on the real production Docker container (`lumen:test`) connected to PostgreSQL:

### Real Measured Benchmark Results

| Stage of Full Workflow | Real Measured Memory | Total RAM Limit | Memory % |
|---|---|---|---|
| **1. Baseline Idle** | **280.9 MiB** | 7.60 GiB | 3.60% |
| **2. Post User Auth & Session Init** | **281.2 MiB** | 7.60 GiB | 3.60% |
| **3. Post 3x CSV Upload (sales, customers, products)** | **307.2 MiB** | 7.60 GiB | 3.94% |
| **4. Post Automated Dashboard Generation** | **308.2 MiB** | 7.60 GiB | 3.95% |
| **5. Post 3 Analytical Questions (PEVN SSE Stream)** | **310.7 MiB** (Peak: **311.3 MiB**) | 7.60 GiB | 3.99% |
| **6. Post PDF Report Export** | **310.8 MiB** | 7.60 GiB | 3.98% |
| **7. Post Admin Console Telemetry & DB Browse** | **311.4 MiB** | 7.60 GiB | 4.00% |

- **Peak Memory Observed**: **311.4 MiB**
- **Safety Ceiling Target**: **450.0 MiB**
- **Render Free Tier Ceiling**: **512.0 MiB**
- **Available Headroom**: **200.6 MiB** (39.2% buffer beneath Render's 512 MB limit)

### Key Memory Architectural Guardrails
1. **Single Worker Async Loop (`WEB_CONCURRENCY=1`)**: Eliminates multi-process RAM multiplication.
2. **Glibc Arena Throttling (`MALLOC_ARENA_MAX=2`)**: Reduces heap fragmentation and prevents virtual memory bloat.
3. **Lazy Schema & Embeddings**: Column search uses lightweight TF-IDF indexing (< 30 MB) instead of eagerly preloading bulky ONNX neural models.

---

## 6. Local Preflight Verification

Before deploying, verify your configuration locally using the preflight validator:

```bash
# Run local deployment preflight
python scripts/preflight_render.py

# Or via Makefile
make preflight
```

The script validates:
- `render.yaml` blueprint structure.
- Root single-service `Dockerfile` multi-stage targets.
- Environment variables without exposing secret values.
- Memory configuration flags.

---

## 7. Storage Trade-offs & Persistent Disks

### Free Tier Ephemeral Storage
On the Render free tier, local disk files under `/app/data` (including DuckDB tenant databases) are stored on an ephemeral filesystem. If the container sleeps after inactivity or restarts during a deployment:
- User accounts, session history, messages, audit logs, and settings remain safe in PostgreSQL.
- Uploaded CSVs and cached DuckDB files are cleared and require re-uploading upon fresh login.

### Adding a Persistent Disk (Production Paid Plan)
To persist DuckDB databases across container restarts:
1. Upgrade service to a paid instance (e.g. Starter $7/mo).
2. In the Render Dashboard, go to **Disks > Add Disk**.
3. Name: `lumen-data`, Mount Path: `/app/data`, Size: `10 GB`.
4. DuckDB columnar databases will persist across all deployments and restarts.

---

## 8. Troubleshooting Guide

| Issue | Root Cause | Solution |
|---|---|---|
| `502 Bad Gateway` on startup | Required production environment variable missing | Check Render logs. Lumen preflight logs missing variable names and exits cleanly if `ADMIN_PASSWORD` < 14 chars or `SECRET_KEY` is insecure. |
| `connection to server at "..." failed: SSL SYSCALL error` | Missing or mismatched SSL mode | Ensure `DATABASE_URL` ends with `sslmode=require` or is normalized automatically by Lumen. |
| `prepared statement "__asyncpg_stmt_..." already exists` | Transaction pooler collision | Normal behavior with PgBouncer. Lumen automatically disables prepared statements via `prepare_threshold=None`. |
| `429 TOO_MANY_REQUESTS` on `/api/v1/admin/login` | Exceeded 5 failed login attempts in 15 minutes | Wait 15 minutes for the lockout window to expire, or restart the container to clear in-memory rate limiting. |
| `column "is_active" is of type boolean but default expression is of type integer` | Migration default mismatch | Fixed in Alembic revision `0001_initial_schema.py` using `sa.text('true')` / `sa.text('false')`. |
