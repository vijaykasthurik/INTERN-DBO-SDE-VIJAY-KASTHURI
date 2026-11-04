# Lumen System Architecture & Technical Specifications

> Production-grade, verified conversational business intelligence platform powered by DuckDB, evidence-grounded parallel DAG execution, and dual-pass cross-verification.

---

## 1. System Context Diagram (C4 Level 1)

```mermaid
flowchart TD
    User([Business Analyst / Executive])
    
    subgraph LumenPlatform [Lumen Platform]
        WebClient[Vite + React 18 + TS Frontend\nDesign System: Editorial White / Capsule Nav]
        APIGateway[FastAPI Gateway\nAsync REST + SSE Streaming]
        AgentEngine[PEVN Agent Engine\nRouter, DAG Planner, Repair Loop]
        EvidenceStore[(Evidence Ledger\nAudit Trail of Code & Row Previews)]
        TenantDB[(Per-User DuckDB\nIsolated Analytical Storage)]
        MetadataDB[(SQLite Metadata\nSessions, Users, Metrics, Traces)]
    end
    
    subgraph LLMProviders [LLM Router & Fallback Chain]
        MockProvider[Deterministic Mock Tier\nZero Keys Required / Offline]
        Gemini[Google Gemini API]
        Groq[Groq LPU Engine]
        OpenRouter[OpenRouter Gateway]
    end

    User <-->|HTTPS / Interactive UI| WebClient
    WebClient <-->|REST API + SSE Stream| APIGateway
    APIGateway <--> AgentEngine
    AgentEngine <-->|Tenant Queries| TenantDB
    AgentEngine <-->|Audit Ledger| EvidenceStore
    APIGateway <-->|State & Auth| MetadataDB
    AgentEngine <-->|Token Bucket Router| LLMProviders
```

---

## 2. Data Onboarding & Ingestion Pipeline (Phase A)

```mermaid
flowchart TD
    Upload[Multi-File CSV Upload] --> Validate[Validator\nEncoding, Delimiter, Size <= 100MB]
    Validate --> Ingest[DuckDB Ingestion Pipeline\nSanitized Identifiers, SQL Keyword Escaping]
    Ingest --> Profiler[Statistical Column Profiler\nMin, Max, Mean, Quartiles, Distinct]
    Profiler --> Auditor[Data Health Auditor\nDuplicates, Missing, Impossible Values, Outliers]
    Auditor --> Score[0-100 Data Health Score Ring]
    
    Ingest --> Relationships[Relationship Detector\nName Similarity + Value Overlap Scoring]
    Relationships --> Graph[Multi-Table Relational Graph]
    
    Profiler --> SemanticLayer[Semantic Layer Catalog\nLLM Inferred Descriptions, Business Metrics]
    SemanticLayer --> CompactCatalog[Compact Catalog JSON\nPrompt Token Efficient View]
```

---

## 3. The PEVN Question Loop Sequence Diagram (Phase B)

The **Plan-Execute-Verify-Narrate (PEVN)** pipeline guarantees that every number in a user response is grounded in raw data execution.

```mermaid
sequenceDiagram
    autonumber
    actor User as User Browser
    participant API as FastAPI Gateway
    participant Context as Context Resolver & Memory
    participant Router as 8-Lane Intent Router
    participant Planner as DAG Planner (Kahn's Waves)
    participant Executor as Concurrent Tool Executor
    participant Tools as DuckDB & Pandas Tools
    participant Ledger as Evidence Ledger
    participant Verifier as Skeptic Verifier (Dual-Pass)
    participant Narrator as Grounded Narrator

    User->>API: POST /chat/sessions/{id}/messages (SSE Stream)
    API->>Context: Resolve Follow-Ups & Entity References
    Context->>Router: Classify Intent (quick_lookup, analysis, anomaly, etc.)
    Router-->>API: SSE: event: route
    API-->>User: Route Event Rendered
    
    Router->>Planner: Formulate Directed Acyclic Graph (DAG)
    Planner-->>API: SSE: event: plan
    API-->>User: Animated Timeline Nodes Generated

    loop Wave Scheduling (Parallel Execution)
        Planner->>Executor: Schedule Wave k Steps
        Executor->>Tools: Run DuckDB SQL / Sandboxed Pandas
        Tools-->>Executor: Raw Table Result + Runtime
        Executor->>Ledger: Append Evidence Entry {step_id, tool, code, rows, runtime}
        Executor-->>API: SSE: event: step_start / step_result
        API-->>User: Nodes Light Up, Spinner -> Checkmark
    end

    Executor->>Verifier: Audit Draft Results
    Verifier->>Tools: Independent Cross-Check (Pandas vs SQL)
    Verifier->>Verifier: Number Grounding Check (Redact Ungrounded Numbers)
    Verifier-->>API: SSE: event: verify (High/Medium/Low Confidence)
    API-->>User: Verifier Checklist & Confidence Badge
    
    Verifier->>Narrator: Authorized Evidence Ledger
    Narrator-->>API: SSE: event: token (Streaming Text with Soft Caret)
    Narrator-->>API: SSE: event: chart (Neutral ECharts Spec)
    Narrator-->>API: SSE: event: final (Structured Markdown + 3 Follow-Ups)
    API-->>User: Final Verified Answer Displayed
```

---

## 4. Database Models & Tenant Isolation ER Diagram

```mermaid
erDiagram
    USERS ||--o{ DATASETS : owns
    USERS ||--o{ CHAT_SESSIONS : conducts
    USERS ||--o{ METRIC_DEFINITIONS : registers
    DATASETS ||--o{ DATASET_COLUMNS : contains
    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : holds
    CHAT_MESSAGES ||--o{ EVIDENCE_ENTRIES : proves

    USERS {
        int id PK
        string email UK
        string hashed_password
        boolean is_active
        datetime created_at
    }

    DATASETS {
        int id PK
        int user_id FK
        string name
        string duckdb_table_name
        int row_count
        int column_count
        float quality_score
        json quality_summary
        datetime created_at
    }

    DATASET_COLUMNS {
        int id PK
        int dataset_id FK
        string name
        string sanitized_name
        string data_type
        text description
        json profile_stats
    }

    CHAT_SESSIONS {
        string id PK
        int user_id FK
        string title
        datetime created_at
        datetime updated_at
    }

    CHAT_MESSAGES {
        string id PK
        string session_id FK
        string role
        text content
        json chart_spec
        string confidence
        json evidence_ledger
        datetime created_at
    }

    METRIC_DEFINITIONS {
        int id PK
        int user_id FK
        int dataset_id FK
        string name
        string expression
        text description
        datetime created_at
    }
```

---

## 5. Security Architecture & Boundary Model

1. **Analytical Data Isolation (P6)**:
   - Each authenticated user is allocated an isolated DuckDB file (`data/user_warehouses/user_{id}.duckdb`).
   - SQLite queries enforce tenant constraints via `user_id == current_user.id`.
2. **SELECT-Only SQL Validator**:
   - Every DuckDB statement is parsed with `sqlglot`.
   - Mutation commands (`DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `COPY`, `ATTACH`) raise immediate `SecurityViolationError`.
   - Automatic `LIMIT 1000` injection prevents memory exhaustion.
3. **AST-Restricted Pandas Sandbox**:
   - Python code is executed in an isolated process with restricted `__builtins__`.
   - Prohibited functions: `eval`, `exec`, `open`, `compile`, `getattr`, `__import__`.
   - Module whitelisting: only `pandas` and `numpy` functions permitted.
4. **Prompt Injection Perimeter**:
   - CSV contents are treated strictly as **DATA**, never as instructions.
   - User prompts are wrapped in an immutable structural template; system instructions cannot be overridden by cell contents.
