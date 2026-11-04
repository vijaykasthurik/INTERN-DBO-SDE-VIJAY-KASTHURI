"""DAG-based Execution Planner for multi-step reasoning."""

from typing import Any

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """Atomic step in a DAG execution plan."""

    id: str
    tool: str
    description: str
    dependencies: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)


class PlanDAG(BaseModel):
    """Directed Acyclic Graph of execution steps."""

    steps: list[PlanStep]


class ExecutionPlanner:
    """Produces dependency DAGs for analytical workflows."""

    def plan(self, question: str, lane: str) -> PlanDAG:
        """Construct parallelizable step DAG."""
        step1 = PlanStep(
            id="step_1",
            tool="sql_tool",
            description="Query DuckDB for target aggregation metrics",
            parameters={"query_intent": question},
        )
        return PlanDAG(steps=[step1])
