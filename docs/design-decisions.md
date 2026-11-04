# Key Design Decisions

## 1. Why the LLM Never Computes
LLMs produce statistically plausible text, not exact arithmetic. In financial and business analytics, an invented number destroys user trust. In Lumen, DuckDB and Pandas compute, and the Evidence Ledger holds the immutable proof.

## 2. Why the Dual-Pass Verifier
Even with deterministic code execution, LLMs can misunderstand a column or drop a filter. The Verifier acts as an adversarial auditor, comparing SQL outputs against an independent Pandas calculation and checking that every number in the draft appears in the ledger.

## 3. Why DuckDB
DuckDB provides sub-millisecond vectorized queries directly over tabular files with native SQL support and low memory overhead, ideal for per-user analytical sandboxes.
