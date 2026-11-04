"""CSV upload endpoints with multi-file support, DuckDB staging, profiling, and quality scoring."""

from fastapi import APIRouter, Depends, File, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import ValidationError
from app.data.persistence import persist_dataset
from app.data.workbook import expand_upload
from app.db.models import User
from app.db.session import get_db
from app.deps import get_current_user

router = APIRouter(prefix="/upload", tags=["upload"])


class UploadedDatasetInfo(BaseModel):
    """Metadata of an uploaded dataset."""

    id: int
    name: str
    table_name: str
    row_count: int
    column_count: int
    quality_score: float


class MultiUploadResponse(BaseModel):
    """Batch upload summary."""

    datasets: list[UploadedDatasetInfo]
    total_files: int
    errors: list[dict[str, str]] = Field(default_factory=list)
    status: str = "success"


@router.post("", response_model=MultiUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_datasets(
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MultiUploadResponse:
    """Accept multi-file CSV uploads, validate, load to DuckDB, profile, and score quality."""
    if not files:
        raise ValidationError("At least one CSV file must be provided")

    uploaded_list: list[UploadedDatasetInfo] = []

    errors: list[dict[str, str]] = []
    prepared: list[tuple[str, bytes, str]] = []
    for file in files:
        filename = file.filename or "dataset.csv"
        try:
            prepared.extend((name,content,filename) for name,content in expand_upload(filename, await file.read(), get_settings().max_upload_mb))
        except ValidationError as exc:
            errors.append({"file": filename, "error": str(exc)})

    for filename, content_bytes, source_filename in prepared:

        try:
            dataset = persist_dataset(db, user, filename, content_bytes, source_filename=source_filename)
        except ValidationError as exc:
            db.rollback()
            errors.append({"file": filename, "error": str(exc)})
            continue

        uploaded_list.append(
            UploadedDatasetInfo(
                id=dataset.id,
                name=dataset.name,
                table_name=dataset.duckdb_table_name,
                row_count=dataset.row_count,
                column_count=dataset.column_count,
                quality_score=dataset.quality_score,
            )
        )

    if not uploaded_list:
        raise ValidationError("; ".join(f"{item['file']}: {item['error']}" for item in errors))
    return MultiUploadResponse(
        datasets=uploaded_list,
        total_files=len(files),
        errors=errors,
        status="partial" if errors else "success",
    )
