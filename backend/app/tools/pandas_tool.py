"""Sandboxed Pandas tool for secondary cross-checks and complex transformations."""

from typing import Any

import pandas as pd

from app.safety.pandas_sandbox import PandasSandbox


class PandasTool:
    """Runs data manipulation in restricted AST sandbox for cross-checking."""

    def __init__(self) -> None:
        self.sandbox = PandasSandbox()

    def execute_script(self, code_str: str, dataframes: dict[str, pd.DataFrame]) -> Any:
        """Execute sandboxed calculation against provided dataframes."""
        local_scope: dict[str, Any] = {"pd": pd, **dataframes}
        return self.sandbox.execute(code_str, local_scope)
