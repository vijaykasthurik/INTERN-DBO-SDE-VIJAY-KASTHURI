"""Unit tests proving concurrent DAG wave execution and cycle detection in PlanDAG."""

import time

import pytest

from app.agent.executor import StepExecutor
from app.agent.ledger import EvidenceLedger
from app.agent.planner import PlanDAG, PlanStep


class MockAsyncTool:
    """Tool that sleeps to simulate execution duration."""

    def __init__(self, delay_sec: float = 0.2) -> None:
        self.delay_sec = delay_sec

    def execute(self, *args, **kwargs):
        time.sleep(self.delay_sec)
        return {"rows": [{"val": 1}], "row_count": 1}


@pytest.mark.asyncio
async def test_parallel_execution_proves_concurrency() -> None:
    """Verify that independent steps in the same execution wave execute concurrently."""
    delay = 0.2
    tool = MockAsyncTool(delay_sec=delay)
    tools = {"sql_tool": tool}
    executor = StepExecutor(tools_registry=tools)
    ledger = EvidenceLedger()

    # Step 1 and Step 2 both have 0 dependencies (Wave 0)
    step1 = PlanStep(
        id="step_1", tool="sql_tool", description="Independent step 1", dependencies=[]
    )
    step2 = PlanStep(
        id="step_2", tool="sql_tool", description="Independent step 2", dependencies=[]
    )
    dag = PlanDAG(steps=[step1, step2])

    waves = dag.get_execution_waves()
    assert len(waves) == 1
    assert len(waves[0]) == 2  # Both steps in wave 0

    start_time = time.perf_counter()
    await executor.execute_dag(dag, ledger)
    elapsed = time.perf_counter() - start_time

    # If run sequentially, elapsed would be >= 0.4s (2 * delay).
    # Running concurrently in parallel, elapsed should be substantially less than 0.35s!
    assert elapsed < 0.38, (
        f"Steps executed sequentially instead of in parallel! Elapsed: {elapsed:.2f}s"
    )
    assert len(ledger.entries) == 2


def test_dag_cycle_detection() -> None:
    """Verify PlanDAG raises ValueError when a cyclic dependency is introduced."""
    step1 = PlanStep(id="step_1", tool="sql_tool", description="Step 1", dependencies=["step_2"])
    step2 = PlanStep(id="step_2", tool="sql_tool", description="Step 2", dependencies=["step_1"])
    cyclic_dag = PlanDAG(steps=[step1, step2])

    with pytest.raises(ValueError) as exc_info:
        cyclic_dag.validate_dag()
    assert "Cycle detected" in str(exc_info.value)


def test_dag_missing_dependency_detection() -> None:
    """Verify PlanDAG detects non-existent dependency references."""
    step1 = PlanStep(
        id="step_1", tool="sql_tool", description="Step 1", dependencies=["ghost_step"]
    )
    dag = PlanDAG(steps=[step1])

    with pytest.raises(ValueError) as exc_info:
        dag.validate_dag()
    assert "references non-existent dependency" in str(exc_info.value)
