"""Ingestion edge cases: empty files, duplicate headers, SQL keywords, and malicious filenames."""

import pytest

from app.core.errors import ValidationError
from app.data.ingestion import DataIngestionPipeline
from app.data.validation import CSVValidator


def test_empty_file_rejected():
    """Verify that empty files (0 bytes) raise a clear ValidationError."""
    validator = CSVValidator()
    with pytest.raises(ValidationError, match="is empty"):
        validator.validate_file(b"", "empty.csv")


def test_duplicate_headers_rejected():
    """Verify that files with duplicate header column names are rejected."""
    validator = CSVValidator()
    bad_csv = b"region,sales,region\nNorth,100,South\n"
    with pytest.raises(ValidationError, match="duplicate header columns"):
        validator.validate_file(bad_csv, "duplicates.csv")


def test_utf8_bom_and_latin1_encoding_sniffing():
    """Verify that UTF-8 with BOM and Latin-1 accented bytes are detected and parsed."""
    validator = CSVValidator()
    # UTF-8 BOM
    bom_csv = b"\xef\xbb\xbfregion,revenue\nEMEA,500\n"
    res = validator.validate_file(bom_csv, "bom.csv")
    assert res.encoding == "utf-8-sig"
    assert res.headers == ["region", "revenue"]

    # Latin-1 with accented characters
    latin1_csv = "ville,cout\nParis,100£\n".encode("latin-1")
    res_lat = validator.validate_file(latin1_csv, "latin.csv")
    assert res_lat.headers[0] == "ville"


def test_file_size_limit_exceeded():
    """Verify files larger than configured MAX_UPLOAD_MB raise clear validation errors."""
    validator = CSVValidator(max_upload_mb=1)  # 1MB limit for testing
    huge_payload = b"col1,col2\n" + (b"val1,val2\n" * 150_000)  # ~1.5MB
    with pytest.raises(ValidationError, match="exceeds limit"):
        validator.validate_file(huge_payload, "large.csv")


def test_sql_keyword_column_names_sanitization():
    """Verify reserved SQL keywords (select, from, group, order) are sanitized safely."""
    validator = CSVValidator()
    csv_with_keywords = b"select,from,where,group,order\n1,2,3,4,5\n"
    res = validator.validate_file(csv_with_keywords, "keywords.csv")
    assert res.sanitized_headers == ["select_val", "from_val", "where_val", "group_val", "order_val"]


def test_malicious_filenames_sanitization():
    """Verify path traversal and SQL injection in filenames are safely sanitized."""
    pipeline = DataIngestionPipeline()
    assert pipeline.sanitize_table_name("../../etc/passwd.csv") == "passwd"
    assert pipeline.sanitize_table_name("<script>alert(1)</script>.csv") in ["script", "script_alert_1_script"]
    assert pipeline.sanitize_table_name("t; DROP TABLE users;--.csv") == "t_drop_table_users"
    assert pipeline.sanitize_table_name("123_numeric.csv") == "t_123_numeric"
