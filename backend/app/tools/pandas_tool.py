"""Sandboxed Pandas tool for secondary cross-checks and complex transformations."""

import json
from typing import Any

import duckdb
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


    @staticmethod
    def load_dataframes(db_path: str, tables: list[str], max_rows: int = 100000) -> dict[str, Any]:
        con = duckdb.connect(db_path,read_only=True)
        frames: dict[str, pd.DataFrame] = {}
        remaining = max_rows
        try:
            for table in tables:
                count = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()
                count_value = int(count[0]) if count else 0
                remaining -= count_value
                if remaining < 0:
                    raise ValueError("Pandas execution exceeds the row budget. Use SQL for this dataset size.")
                frames[table] = con.execute(f'SELECT * FROM "{table}"').df()
        finally:
            con.close()
        primary = "sales" if "sales" in frames else next(iter(frames), None)
        return {"dataframes":frames, **({"df":frames[primary]} if primary else {})}

    @staticmethod
    def result_rows(value: Any) -> tuple[list[str], list[dict[str, Any]]]:
        if isinstance(value,pd.Series):
            value = value.to_frame()
        if isinstance(value,pd.DataFrame):
            frame = value
        elif isinstance(value,list):
            frame = pd.DataFrame(value)
        elif isinstance(value,dict):
            frame = pd.DataFrame([value])
        else:
            frame = pd.DataFrame([{"result":value}])
        frame = frame.head(1000)
        rows: list[dict[str, Any]] = json.loads(frame.to_json(orient="records",date_format="iso"))
        return [str(column) for column in frame.columns],rows
