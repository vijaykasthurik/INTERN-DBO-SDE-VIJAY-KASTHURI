# Lumen System Architecture

```mermaid
flowchart TD
    User([User Browser]) -->|Natural Language Query| FastAPIGateway[FastAPI Gateway]
    FastAPIGateway --> ContextResolver[Context Resolver]
    ContextResolver --> IntentRouter[Intent Router]
    
    IntentRouter -->|DAG Steps| ExecutionPlanner[Execution Planner]
    ExecutionPlanner --> StepExecutor[Step Executor]
    
    subgraph Execution & Data Layer
        StepExecutor --> SQLTool[DuckDB SQL Tool]
        StepExecutor --> PandasTool[Sandboxed Pandas Tool]
        StepExecutor --> AnomalyTool[Anomaly Ensemble]
        StepExecutor --> ForecastTool[Holt-Winters Forecaster]
        
        SQLTool --> DuckDB[(Per-User DuckDB)]
        PandasTool --> ASTSandbox[Restricted AST Sandbox]
    end
    
    StepExecutor --> EvidenceLedger[Evidence Ledger]
    EvidenceLedger --> Verifier[Dual-Pass Verifier]
    Verifier -->|Cross-Checked & Grounded| Narrator[Grounded Narrator]
    Narrator -->|SSE Event Stream| User
```

## Core Tenets
1. **P1 - No LLM Computation**: The LLM writes code; DuckDB/Pandas compute.
2. **P2 - Engineered Trust**: The Verifier audits every answer before user visibility.
3. **P6 - Read-Only Analytical Isolation**: SELECT-only allowlist and tenant separation.
