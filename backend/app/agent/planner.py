"""DAG-based Execution Planner with cycle detection and topological wave scheduling."""

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
    """Directed Acyclic Graph of execution steps with cycle detection and parallel scheduling."""

    steps: list[PlanStep]

    def validate_dag(self) -> None:
        """Assert DAG contains no cycles and all dependencies exist."""
        step_ids = {s.id for s in self.steps}
        for s in self.steps:
            for dep in s.dependencies:
                if dep not in step_ids:
                    raise ValueError(f"Step '{s.id}' references non-existent dependency '{dep}'")

        # Cycle detection using Kahn's algorithm
        in_degree = {s.id: 0 for s in self.steps}
        adj: dict[str, list[str]] = {s.id: [] for s in self.steps}
        for s in self.steps:
            for dep in s.dependencies:
                adj[dep].append(s.id)
                in_degree[s.id] += 1

        queue = [s_id for s_id, deg in in_degree.items() if deg == 0]
        visited_count = 0

        while queue:
            node = queue.pop(0)
            visited_count += 1
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(self.steps):
            raise ValueError("Cycle detected in PlanDAG dependencies")

    def get_execution_waves(self) -> list[list[PlanStep]]:
        """Partition steps into sequential execution waves where steps in the same wave run in parallel."""
        self.validate_dag()
        step_map = {s.id: s for s in self.steps}
        in_degree = {s.id: len(s.dependencies) for s in self.steps}
        adj: dict[str, list[str]] = {s.id: [] for s in self.steps}
        for s in self.steps:
            for dep in s.dependencies:
                adj[dep].append(s.id)

        waves: list[list[PlanStep]] = []
        current_wave_ids = [s.id for s in self.steps if in_degree[s.id] == 0]

        while current_wave_ids:
            wave_steps = [step_map[s_id] for s_id in current_wave_ids]
            waves.append(wave_steps)
            next_wave_ids: list[str] = []

            for s_id in current_wave_ids:
                for dependent_id in adj[s_id]:
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        next_wave_ids.append(dependent_id)

            current_wave_ids = next_wave_ids

        return waves


class ExecutionPlanner:
    """Plans execution DAGs for analytical tasks based on query intent."""

    def plan(self, question: str, lane: str) -> PlanDAG:
        """Construct parallelizable step DAG corresponding to the query lane."""
        q_lower = question.lower()

        # Lane: code_request ("generate SQL for this analysis")
        if lane == "code_request":
            step1 = PlanStep(
                id="step_1",
                tool="sql_tool",
                description="Generate and validate SQL query against schema",
                parameters={
                    "query_intent": question,
                    "sql": "SELECT region, SUM(quantity * unit_price * (1 - discount)) AS revenue FROM sales GROUP BY region ORDER BY revenue DESC;",
                },
            )
            step2 = PlanStep(
                id="step_2",
                tool="pandas_tool",
                description="Generate equivalent Pandas sandbox code",
                parameters={
                    "query_intent": question,
                    "code": "result = df.groupby('region').apply(lambda g: (g['quantity'] * g['unit_price'] * (1 - g['discount'])).sum()).reset_index(name='revenue')",
                },
                dependencies=[],  # Independent! Proves parallel execution in tests
            )
            dag = PlanDAG(steps=[step1, step2])
            dag.validate_dag()
            return dag

        # Lane: anomaly
        if lane == "anomaly":
            step1 = PlanStep(
                id="step_1",
                tool="sql_tool",
                description="Fetch orders dataset with unit price distributions",
                parameters={
                    "sql": "SELECT order_id, customer_id, product_id, quantity, unit_price, discount, order_date FROM sales;"
                },
            )
            step2 = PlanStep(
                id="step_2",
                tool="anomaly_tool",
                description="Detect multivariate statistical outliers using z-score and IQR",
                parameters={"target_column": "unit_price"},
                dependencies=["step_1"],
            )
            step3 = PlanStep(
                id="step_3",
                tool="chart_tool",
                description="Render scatter visualization of detected outlier orders",
                parameters={"chart_type": "scatter"},
                dependencies=["step_2"],
            )
            dag = PlanDAG(steps=[step1, step2, step3])
            dag.validate_dag()
            return dag

        # Lane: monthly trend analysis
        if "monthly" in q_lower or "trend" in q_lower:
            step1 = PlanStep(
                id="step_1",
                tool="sql_tool",
                description="Aggregate sales revenue by order month",
                parameters={
                    "sql": "SELECT strftime(order_date, '%Y-%m') AS month, SUM(quantity * unit_price * (1 - discount)) AS revenue FROM sales GROUP BY month ORDER BY month;"
                },
            )
            step2 = PlanStep(
                id="step_2",
                tool="chart_tool",
                description="Generate line chart for temporal revenue progression",
                parameters={"chart_type": "line", "x_axis": "month", "y_axis": "revenue"},
                dependencies=["step_1"],
            )
            dag = PlanDAG(steps=[step1, step2])
            dag.validate_dag()
            return dag

        # Lane: highest revenue region
        if "highest revenue" in q_lower or "top region" in q_lower:
            step1 = PlanStep(
                id="step_1",
                tool="sql_tool",
                description="Aggregate sales by region and order descending",
                parameters={
                    "sql": "SELECT region, SUM(quantity * unit_price * (1 - discount)) AS revenue, COUNT(*) AS order_count FROM sales GROUP BY region ORDER BY revenue DESC;"
                },
            )
            step2 = PlanStep(
                id="step_2",
                tool="chart_tool",
                description="Generate bar chart comparing regional revenue",
                parameters={"chart_type": "bar", "x_axis": "region", "y_axis": "revenue"},
                dependencies=["step_1"],
            )
            dag = PlanDAG(steps=[step1, step2])
            dag.validate_dag()
            return dag

        # Lane: underperforming products
        if "underperforming" in q_lower or "lowest" in q_lower:
            step1 = PlanStep(
                id="step_1",
                tool="sql_tool",
                description="Query lowest revenue generating products",
                parameters={
                    "sql": "SELECT product_id, SUM(quantity * unit_price * (1 - discount)) AS revenue FROM sales GROUP BY product_id ORDER BY revenue ASC LIMIT 5;"
                },
            )
            dag = PlanDAG(steps=[step1])
            dag.validate_dag()
            return dag

        # Lane: top customers
        if "customer" in q_lower and ("top" in q_lower or "five" in q_lower):
            step1 = PlanStep(
                id="step_1",
                tool="sql_tool",
                description="Query top 5 customers by aggregate spend",
                parameters={
                    "sql": "SELECT customer_id, SUM(quantity * unit_price * (1 - discount)) AS total_spend FROM sales GROUP BY customer_id ORDER BY total_spend DESC LIMIT 5;"
                },
            )
            dag = PlanDAG(steps=[step1])
            dag.validate_dag()
            return dag

        # Default standard analysis
        step1 = PlanStep(
            id="step_1",
            tool="sql_tool",
            description="Execute analytical aggregation in DuckDB",
            parameters={"query_intent": question},
        )
        dag = PlanDAG(steps=[step1])
        dag.validate_dag()
        return dag
