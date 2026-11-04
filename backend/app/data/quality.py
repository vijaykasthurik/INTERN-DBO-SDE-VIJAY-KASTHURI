"""Data Quality Auditor: Evaluates duplicates, missing values, impossible metrics, and anomalies."""

from typing import Any
import duckdb


def _fetch_count(con: Any, query: str) -> int:
    row = con.execute(query).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


class QualityAuditor:
    """Computes explainable 0-100 data health scores with diagnostic issue deductions."""

    def evaluate_table_quality(self, db_path: str, table_name: str) -> dict[str, Any]:
        """Perform comprehensive data quality inspection on a DuckDB table."""
        con = duckdb.connect(db_path, read_only=True)
        issues: list[dict[str, Any]] = []
        score = 100.0

        try:
            total_rows = _fetch_count(con, f'SELECT COUNT(*) FROM "{table_name}";')
            if total_rows == 0:
                return {
                    "score": 0.0,
                    "issues": [{"category": "empty", "severity": "critical", "description": "Table contains 0 rows"}],
                    "summary": "Table is completely empty.",
                }

            columns_desc = con.execute(f'DESCRIBE "{table_name}";').fetchall()
            col_names = [r[0] for r in columns_desc]

            # 1. Duplicate Row Check
            col_list_str = ", ".join(f'"{c}"' for c in col_names)
            dup_query = f'''
                SELECT COUNT(*) FROM (
                    SELECT {col_list_str}, COUNT(*) AS c
                    FROM "{table_name}"
                    GROUP BY {col_list_str}
                    HAVING c > 1
                );
            '''
            duplicate_blocks = _fetch_count(con, dup_query)
            if duplicate_blocks > 0:
                deduction = min(15.0, duplicate_blocks * 2.0)
                score -= deduction
                issues.append({
                    "category": "duplicates",
                    "severity": "medium",
                    "description": f"Found {duplicate_blocks} duplicated row groups in dataset",
                    "deduction": deduction,
                })

            # 2. Missing Values Check
            for col in col_names:
                null_count = _fetch_count(con, f'SELECT COUNT(*) FROM "{table_name}" WHERE "{col}" IS NULL;')
                if null_count > 0:
                    null_pct = (null_count / total_rows) * 100.0
                    deduction = min(10.0, round(null_pct * 0.5, 1))
                    score -= deduction
                    issues.append({
                        "category": "missing_values",
                        "severity": "low" if null_pct < 10 else "medium",
                        "column": col,
                        "description": f"Column '{col}' has {null_count} missing values ({null_pct:.1f}%)",
                        "deduction": deduction,
                    })

            # 3. Constant Columns Check
            for col in col_names:
                distinct_count = _fetch_count(con, f'SELECT COUNT(DISTINCT "{col}") FROM "{table_name}";')
                if distinct_count == 1:
                    score -= 5.0
                    issues.append({
                        "category": "constant_column",
                        "severity": "low",
                        "column": col,
                        "description": f"Column '{col}' is constant (zero variance across all rows)",
                        "deduction": 5.0,
                    })

            # 4. Impossible Numerical Values Check (e.g. negative price or discount > 1.0)
            for col in col_names:
                col_lower = col.lower()
                if "price" in col_lower or "unit_price" in col_lower or "amount" in col_lower:
                    neg_prices = _fetch_count(con, f'SELECT COUNT(*) FROM "{table_name}" WHERE "{col}" < 0;')
                    if neg_prices > 0:
                        score -= 15.0
                        issues.append({
                            "category": "impossible_value",
                            "severity": "high",
                            "column": col,
                            "description": f"Column '{col}' contains {neg_prices} negative price values",
                            "deduction": 15.0,
                        })

                if "discount" in col_lower:
                    bad_discounts = _fetch_count(con, f'SELECT COUNT(*) FROM "{table_name}" WHERE "{col}" < 0 OR "{col}" > 1.0;')
                    if bad_discounts > 0:
                        score -= 10.0
                        issues.append({
                            "category": "impossible_value",
                            "severity": "medium",
                            "column": col,
                            "description": f"Column '{col}' contains {bad_discounts} invalid discounts (< 0 or > 1.0)",
                            "deduction": 10.0,
                        })

            # Clamp score between 0 and 100
            final_score = max(0.0, min(100.0, round(score, 1)))

            summary = (
                f"Overall Data Health: {final_score}/100. "
                f"{len(issues)} data quality observations noted."
            )

            return {
                "score": final_score,
                "issues": issues,
                "summary": summary,
            }

        finally:
            con.close()
