import io
import zipfile

import duckdb
import pytest
from openpyxl import Workbook

from app.core.errors import ValidationError
from app.data.ingestion import DataIngestionPipeline
from app.data.workbook import expand_upload


def test_all_sheets_follow_csv_validation_and_real_ingestion(tmp_path):
    book = Workbook()
    sheet = book.active
    sheet.title = "Orders"
    sheet.append(["customer_id", "revenue"])
    sheet.append(["A", 12.5])
    other = book.create_sheet("Customers")
    other.append(["customer_id", "segment"])
    other.append(["A", "Enterprise"])
    stream = io.BytesIO()
    book.save(stream)
    expanded = expand_upload("business.xlsx", stream.getvalue(), 50)
    assert len(expanded) == 2
    pipeline = DataIngestionPipeline(data_dir=str(tmp_path))
    for name, content in expanded:
        result = pipeline.ingest_csv(1, name, content)
        assert result["row_count"] == 1
    con = duckdb.connect(pipeline.get_user_db_path(1), read_only=True)
    assert con.execute('SELECT SUM(revenue) FROM business_orders JOIN business_customers USING(customer_id)').fetchone()[0] == 12.5
    con.close()


def test_corrupt_legacy_and_expansion_limits():
    with pytest.raises(ValidationError, match="corrupt or password-protected"):
        expand_upload("bad.xlsx", b"not an excel file", 50)
    with pytest.raises(ValidationError, match="Legacy"):
        expand_upload("old.xls", b"old format", 50)
    bomb = io.BytesIO()
    with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("large", b"0" * (11*1024*1024))
    with pytest.raises(ValidationError, match="Expanded workbook"):
        expand_upload("bomb.xlsx", bomb.getvalue(), 1)
