# Lumen Evaluation Harness

Provides automated evaluation against the golden benchmark ground truth (`eval/golden.yaml`).

## Metrics Computed
- **Execution Accuracy**: % of queries yielding mathematically equivalent result sets.
- **Verifier Catch Rate**: % of injected hallucinated numbers intercepted by the skeptic.
- **Average Latency**: Response generation time in milliseconds.
- **Cache Hit Rate**: Re-query retrieval performance.
