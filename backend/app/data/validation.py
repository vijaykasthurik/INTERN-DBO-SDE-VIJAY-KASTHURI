"""CSV Validation module: checks encoding, delimiters, header integrity, and limits."""

import csv
import io
import re

from app.core.errors import ValidationError


class CSVValidationResult:
    """Detailed outcome of CSV structural and format inspection."""

    def __init__(
        self,
        valid: bool,
        filename: str,
        encoding: str,
        delimiter: str,
        headers: list[str],
        sanitized_headers: list[str],
        row_count: int,
        column_count: int,
        size_bytes: int,
    ) -> None:
        self.valid = valid
        self.filename = filename
        self.encoding = encoding
        self.delimiter = delimiter
        self.headers = headers
        self.sanitized_headers = sanitized_headers
        self.row_count = row_count
        self.column_count = column_count
        self.size_bytes = size_bytes


class CSVValidator:
    """Validates uploaded CSV files against security and schema constraints."""

    SQL_RESERVED_WORDS = {
        "SELECT", "FROM", "WHERE", "GROUP", "ORDER", "BY", "LIMIT",
        "JOIN", "INNER", "LEFT", "RIGHT", "OUTER", "TABLE", "USER",
        "PRIMARY", "KEY", "INDEX", "AS", "HAVING", "DISTINCT", "ON",
    }

    def __init__(
        self,
        max_upload_mb: int = 50,
        max_rows: int = 1_000_000,
        max_columns: int = 500,
    ) -> None:
        self.max_upload_mb = max_upload_mb
        self.max_rows = max_rows
        self.max_columns = max_columns

    def detect_encoding(self, raw_bytes: bytes) -> str:
        """Sniff text encoding using byte patterns."""
        if raw_bytes.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        for enc in ["utf-8", "latin-1", "cp1252", "iso-8859-1"]:
            try:
                raw_bytes[:8192].decode(enc)
                return enc
            except (UnicodeDecodeError, LookupError):
                continue
        return "utf-8"

    def detect_delimiter(self, sample_text: str) -> str:
        """Sniff delimiter among comma, semicolon, tab, pipe."""
        candidates = [",", ";", "\t", "|"]
        counts = {c: sample_text.count(c) for c in candidates}
        best = max(counts, key=counts.get)  # type: ignore[arg-type]
        return best if counts[best] > 0 else ","

    def sanitize_column_name(self, raw_name: str, index: int) -> str:
        """Produce safe DuckDB column identifier avoiding collision and SQL keywords."""
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", raw_name.strip()).lower()
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")

        if not cleaned:
            return f"col_{index + 1}"
        if cleaned[0].isdigit():
            cleaned = f"col_{cleaned}"
        if cleaned.upper() in self.SQL_RESERVED_WORDS:
            cleaned = f"{cleaned}_val"

        return cleaned

    def validate_file(self, content_bytes: bytes, filename: str) -> CSVValidationResult:
        """Inspect file content, asserting validity and returning structural metadata."""
        size_bytes = len(content_bytes)
        if size_bytes == 0:
            raise ValidationError(f"File '{filename}' is empty (0 bytes)")

        size_mb = size_bytes / (1024 * 1024)
        if size_mb > self.max_upload_mb:
            raise ValidationError(
                f"File '{filename}' size ({size_mb:.2f}MB) exceeds limit of {self.max_upload_mb}MB"
            )

        encoding = self.detect_encoding(content_bytes)
        try:
            text = content_bytes.decode(encoding)
        except Exception as exc:
            raise ValidationError(f"Failed to decode file '{filename}' with {encoding}: {exc}") from exc

        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            raise ValidationError(f"File '{filename}' contains no readable lines")

        delimiter = self.detect_delimiter(lines[0])
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        try:
            headers = next(reader)
        except StopIteration as exc:
            raise ValidationError(f"File '{filename}' has no header line") from exc

        if not headers or all(not h.strip() for h in headers):
            raise ValidationError(f"File '{filename}' has an empty header row")

        # Check duplicate headers
        seen_headers: set[str] = set()
        duplicates: list[str] = []
        for h in headers:
            norm = h.strip().lower()
            if norm in seen_headers:
                duplicates.append(h)
            seen_headers.add(norm)

        if duplicates:
            raise ValidationError(
                f"File '{filename}' contains duplicate header columns: {', '.join(duplicates)}"
            )

        # Sanitize and check column count
        col_count = len(headers)
        if col_count > self.max_columns:
            raise ValidationError(
                f"File '{filename}' has {col_count} columns, exceeding limit of {self.max_columns}"
            )

        sanitized_headers = [
            self.sanitize_column_name(h, idx) for idx, h in enumerate(headers)
        ]

        # Count data rows
        row_count = sum(1 for _ in reader)
        if row_count > self.max_rows:
            raise ValidationError(
                f"File '{filename}' has {row_count} rows, exceeding limit of {self.max_rows}"
            )

        return CSVValidationResult(
            valid=True,
            filename=filename,
            encoding=encoding,
            delimiter=delimiter,
            headers=headers,
            sanitized_headers=sanitized_headers,
            row_count=row_count,
            column_count=col_count,
            size_bytes=size_bytes,
        )
