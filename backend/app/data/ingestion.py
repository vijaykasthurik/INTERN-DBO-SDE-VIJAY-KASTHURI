"""Data ingestion pipeline: loads validated CSVs into per-user DuckDB databases."""

import io
import os
import re
from typing import Any
import duckdb
import pandas as pd
from app.config import get_settings
from app.core.errors import ValidationError
from app.data.validation import CSVValidationResult, CSVValidator


class DataIngestionPipeline:
    """Manages isolated per-user DuckDB databases and atomic table ingestion."""

    def __init__(self, data_dir: str | None = None) -> None:
        settings = get_settings()
        self.data_dir = data_dir or settings.data_dir
        self.validator = CSVValidator(max_upload_mb=settings.max_upload_mb)

    def get_user_db_path(self, user_id: int) -> str:
        """Derive absolute path to user's isolated DuckDB analytical database."""
        user_dir = os.path.join(self.data_dir, "users", str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        return os.path.join(user_dir, "analytics.duckdb")

    def sanitize_table_name(self, raw_name: str) -> str:
        """Generate safe, collision-proof SQL table identifier from filename."""
        base = os.path.splitext(os.path.basename(raw_name))[0]
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", base.strip()).lower()
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        if not cleaned or cleaned[0].isdigit():
            cleaned = f"t_{cleaned}" if cleaned else "t_dataset"
        return cleaned

    def ingest_csv(
        self,
        user_id: int,
        filename: str,
        content_bytes: bytes,
    ) -> dict[str, Any]:
        """Validate and atomically load CSV bytes into user's DuckDB database."""
        val_result = self.validator.validate_file(content_bytes, filename)
        table_name = self.sanitize_table_name(filename)

        # Parse with pandas using validated encoding and delimiter
        try:
            df = pd.read_csv(
                io.BytesIO(content_bytes),
                encoding=val_result.encoding,
                sep=val_result.delimiter,
            )
        except Exception as exc:
            raise ValidationError(f"Failed to parse CSV tabular data: {exc}") from exc

        # Assign sanitized column names
        df.columns = val_result.sanitized_headers

        db_path = self.get_user_db_path(user_id)
        con = duckdb.connect(db_path)
        try:
            # Create or replace table atomically
            con.register("df_temp_upload", df)
            con.execute(f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM df_temp_upload;')
            con.unregister("df_temp_upload")

            # Introspect column data types
            schema_info = con.execute(f'DESCRIBE "{table_name}";').fetchall()
            columns_meta = [
                {
                    "name": val_result.headers[idx] if idx < len(val_result.headers) else row[0],
                    "sanitized_name": row[0],
                    "data_type": str(row[1]),
                }
                for idx, row in enumerate(schema_info)
            ]

            actual_rows_row = con.execute(f'SELECT COUNT(*) FROM "{table_name}";').fetchone()
            actual_rows = int(actual_rows_row[0]) if actual_rows_row else 0
        finally:
            con.close()

        return {
            "table_name": table_name,
            "row_count": actual_rows,
            "column_count": len(columns_meta),
            "columns": columns_meta,
            "validation": val_result,
            "db_path": db_path,
        }
