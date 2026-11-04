"""Restricted AST Sandbox for executing Pandas computations in an isolated subprocess.

Enforces:
- Restricted AST: no imports, no function/class definitions, no dunder attribute access
- Blocklist of dangerous builtins (eval, exec, open, compile, globals, locals, etc.)
- Strict runtime isolation inside a subprocess with minimal safe builtins
- Strict timeout enforcement to kill infinite loops / CPU exhaustion
"""

import ast
import pickle
import subprocess
import sys
from typing import Any


class SandboxViolationError(Exception):
    """Raised when code violates sandboxing AST security rules or runtime limits."""

    pass


_SUBPROCESS_RUNNER = """
import sys
import pickle
import pandas as pd
import numpy as np
import math

SAFE_BUILTINS = {
    'len': len, 'sum': sum, 'min': min, 'max': max, 'abs': abs,
    'round': round, 'int': int, 'float': float, 'str': str,
    'bool': bool, 'list': list, 'dict': dict, 'set': set,
    'tuple': tuple, 'range': range, 'zip': zip, 'enumerate': enumerate,
    'sorted': sorted, 'True': True, 'False': False, 'None': None,
}

try:
    raw_input = sys.stdin.buffer.read()
    data = pickle.loads(raw_input)
    code_str = data['code']
    local_env = data.get('env', {})
    safe_globals = {
        '__builtins__': SAFE_BUILTINS,
        'pd': pd,
        'np': np,
        'math': math,
    }
    compiled = compile(code_str, '<sandbox>', 'exec')
    exec(compiled, safe_globals, local_env)
    result = local_env.get('result')
    sys.stdout.buffer.write(pickle.dumps({'success': True, 'result': result}))
except Exception as e:
    sys.stdout.buffer.write(pickle.dumps({'success': False, 'error': f'{type(e).__name__}: {e}'}))
"""


class PandasSandbox:
    """Restricted-AST execution sandbox preventing imports, OS access, and dunder methods."""

    # Disallowed AST node types
    DISALLOWED_NODES = (
        ast.Import,
        ast.ImportFrom,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
        ast.Delete,
        ast.Global,
        ast.Nonlocal,
        ast.With,
        ast.AsyncWith,
        ast.Try,
        ast.Raise,
        ast.Assert,
        ast.Yield,
        ast.YieldFrom,
    )

    # Forbidden identifiers and built-in function names
    FORBIDDEN_NAMES = {
        "eval",
        "exec",
        "open",
        "compile",
        "__import__",
        "getattr",
        "setattr",
        "delattr",
        "hasattr",
        "globals",
        "locals",
        "vars",
        "breakpoint",
        "input",
        "exit",
        "quit",
        "help",
        "memoryview",
        "bytearray",
        "bytes",
        "super",
        "property",
        "type",
        "classmethod",
        "staticmethod",
        "os",
        "sys",
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "http",
        "shutil",
    }

    def validate_ast(self, code_str: str) -> None:
        """Parse Python code and ensure no dangerous AST nodes, dunders, or banned names exist."""
        if not code_str or not code_str.strip():
            raise SandboxViolationError("Empty code snippet provided")

        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            raise SandboxViolationError(f"Syntax error in code: {e}") from e

        for node in ast.walk(tree):
            # Check disallowed AST statement/expression types
            if isinstance(node, self.DISALLOWED_NODES):
                raise SandboxViolationError(f"Disallowed syntax construct: {type(node).__name__}")

            # Check dunder and private attribute access
            if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
                raise SandboxViolationError(
                    f"Private or dunder attribute access '{node.attr}' is strictly forbidden"
                )

            # Check forbidden variable/function names
            if isinstance(node, ast.Name):
                if node.id.startswith("_"):
                    raise SandboxViolationError(
                        f"Private or dunder variable '{node.id}' is strictly forbidden"
                    )
                if node.id in self.FORBIDDEN_NAMES:
                    raise SandboxViolationError(
                        f"Forbidden identifier '{node.id}' is strictly prohibited"
                    )

    def execute(self, code_str: str, local_env: dict[str, Any], timeout_sec: float = 5.0) -> Any:
        """Execute validated Pandas snippet within an isolated subprocess with timeout protection."""
        self.validate_ast(code_str)

        payload = pickle.dumps({"code": code_str, "env": local_env})

        try:
            proc = subprocess.run(
                [sys.executable, "-c", _SUBPROCESS_RUNNER],
                input=payload,
                capture_output=True,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired as e:
            raise SandboxViolationError(f"Execution timed out after {timeout_sec}s limit") from e
        except Exception as e:
            raise SandboxViolationError(f"Subprocess runner error: {e}") from e

        if proc.returncode != 0:
            err = proc.stderr.decode("utf-8", errors="replace")
            raise SandboxViolationError(f"Subprocess execution failed: {err}")

        try:
            response = pickle.loads(proc.stdout)
        except Exception as e:
            raise SandboxViolationError(f"Failed to deserialize execution output: {e}") from e

        if not response.get("success", False):
            raise SandboxViolationError(f"Execution error: {response.get('error')}")

        return response.get("result")
