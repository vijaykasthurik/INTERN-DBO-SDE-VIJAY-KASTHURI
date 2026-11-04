"""Statistical profiler for datasets: dtypes, nulls, distinct counts, min/max/mean, top values."""

from typing import Any
import duckdb
import numpy as np


class DatasetProfiler:
    """Profiles tabular columns inside DuckDB connections."""

    def profile_table(self, db_path: str, table_name: str) -> list[dict[str, Any]]:
        """Compute column statistics including distributions, quantiles, and null ratios."""
        con = duckdb.connect(db_path, read_only=True)
        profiles: list[dict[str, Any]] = []

        try:
            tot_row = con.execute(f'SELECT COUNT(*) FROM "{table_name}";').fetchone()
            total_rows = int(tot_row[0]) if tot_row else 0
            columns_desc = con.execute(f'DESCRIBE "{table_name}";').fetchall()

            for col_info in columns_desc:
                col_name = col_info[0]
                dtype = str(col_info[1]).upper()

                # Basic counts
                stats_row = con.execute(f'''
                    SELECT
                        COUNT("{col_name}") AS non_null_count,
                        COUNT(DISTINCT "{col_name}") AS distinct_count
                    FROM "{table_name}";
                ''').fetchone()

                non_null = stats_row[0] if stats_row else 0
                distinct = stats_row[1] if stats_row else 0
                null_count = total_rows - non_null
                null_pct = round((null_count / total_rows * 100.0), 2) if total_rows > 0 else 0.0

                profile: dict[str, Any] = {
                    "column_name": col_name,
                    "dtype": dtype,
                    "total_rows": total_rows,
                    "null_count": null_count,
                    "null_pct": null_pct,
                    "distinct_count": distinct,
                    "is_unique": distinct == total_rows and total_rows > 0,
                    "is_constant": distinct == 1,
                }

                # Numerical statistics
                if any(num_t in dtype for num_t in ["INT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "BIGINT"]):
                    num_stats = con.execute(f'''
                        SELECT
                            MIN("{col_name}"),
                            MAX("{col_name}"),
                            AVG("{col_name}"),
                            MEDIAN("{col_name}"),
                            STDDEV("{col_name}")
                        FROM "{table_name}"
                        WHERE "{col_name}" IS NOT NULL;
                    ''').fetchone()

                    if num_stats and num_stats[0] is not None:
                        profile["min"] = float(num_stats[0])
                        profile["max"] = float(num_stats[1])
                        profile["mean"] = round(float(num_stats[2]), 4) if num_stats[2] is not None else None
                        profile["median"] = round(float(num_stats[3]), 4) if num_stats[3] is not None else None
                        profile["stddev"] = round(float(num_stats[4]), 4) if num_stats[4] is not None else None

                # Top frequent values
                top_values_rows = con.execute(f'''
                    SELECT "{col_name}", COUNT(*) AS cnt
                    FROM "{table_name}"
                    WHERE "{col_name}" IS NOT NULL
                    GROUP BY "{col_name}"
                    ORDER BY cnt DESC
                    LIMIT 5;
                ''').fetchall()
                profile["top_values"] = [{"value": str(r[0]), "count": r[1]} for r in top_values_rows]

                profiles.append(profile)

        finally:
            con.close()

        return profiles
