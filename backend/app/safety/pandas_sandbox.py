"""Restricted AST Sandbox for executing Pandas computations."""

import ast
from typing import Any


class SandboxViolationError(Exception):
    """Raised when code violates sandboxing AST security rules."""
    pass


class PandasSandbox:
    """Restricted-AST execution sandbox preventing imports, OS access, and dunder methods."""

    DISALLOWED_NODES = (
        ast.Import,
        ast.ImportFrom,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
    )

    def validate_ast(self, code_str: str) -> None:
        """Parse Python code and ensure no dangerous AST nodes or dunders exist."""
        tree = ast.parse(code_str)
        for node in ast.walk(tree):
            if isinstance(node, self.DISALLOWED_NODES):
                raise SandboxViolationError(f"Disallowed construct: {type(node).__name__}")
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                raise SandboxViolationError("Dunder attribute access is strictly forbidden")

    def execute(self, code_str: str, local_env: dict[str, Any]) -> Any:
        """Execute validated snippet in restricted scope."""
        self.validate_ast(code_str)
        safe_globals: dict[str, Any] = {"__builtins__": {}}
        exec(code_str, safe_globals, local_env)
        return local_env.get("result")
