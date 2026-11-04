"""Bounded workbook expansion; every worksheet follows the CSV validation pipeline."""
import csv
import io
import zipfile
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from app.core.errors import ValidationError


def expand_upload(filename: str, content: bytes, max_mb: int) -> list[tuple[str, bytes]]:
    extension = Path(filename).suffix.lower()
    if extension in {".csv", ".txt"}:
        return [(filename, content)]
    if extension == ".xls":
        raise ValidationError("Legacy .xls files are not supported. Save the workbook as .xlsx.")
    if extension != ".xlsx":
        raise ValidationError("Upload CSV or Excel .xlsx files.")
    if len(content) > max_mb * 1024 * 1024:
        raise ValidationError("Workbook exceeds the upload size limit.")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if sum(item.file_size for item in archive.infolist()) > max_mb * 1024 * 1024 * 10:
                raise ValidationError("Expanded workbook exceeds the safe size limit.")
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True, keep_links=False)
    except (zipfile.BadZipFile, InvalidFileException, OSError, ValueError, KeyError) as exc:
        raise ValidationError("Workbook is corrupt or password-protected. Upload an unencrypted .xlsx file.") from exc
    outputs: list[tuple[str, bytes]] = []
    try:
        if len(workbook.worksheets) > 100:
            raise ValidationError("Workbook exceeds the 100-sheet limit.")
        for sheet in workbook.worksheets:
            if sheet.max_column and sheet.max_column > 500 or sheet.max_row and sheet.max_row > 1_000_001:
                raise ValidationError(f"Sheet '{sheet.title}' exceeds the row or column limit.")
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            for row in sheet.iter_rows(values_only=True):
                writer.writerow(row)
                if buffer.tell() > max_mb * 1024 * 1024:
                    raise ValidationError(f"Sheet '{sheet.title}' exceeds the expanded upload size limit.")
            outputs.append((f"{Path(filename).stem}__{sheet.title}.csv", buffer.getvalue().encode("utf-8")))
    finally:
        workbook.close()
    if not outputs:
        raise ValidationError("Workbook has no worksheets.")
    return outputs
