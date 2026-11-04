"""CSV upload endpoints with multi-file support, DuckDB staging, profiling, and quality scoring."""

from fastapi import APIRouter, Depends, File, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.data.catalog import SemanticCatalogBuilder
from app.data.ingestion import DataIngestionPipeline
from app.data.profiler import DatasetProfiler
from app.data.quality import QualityAuditor
from app.db.models import Dataset, DatasetColumn, User
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

    pipeline = DataIngestionPipeline()
    profiler = DatasetProfiler()
    auditor = QualityAuditor()
    catalog_builder = SemanticCatalogBuilder()

    uploaded_list: list[UploadedDatasetInfo] = []

    for file in files:
        filename = file.filename or "dataset.csv"
        content_bytes = await file.read()

        # Ingest into user's DuckDB database
        ingest_res = pipeline.ingest_csv(
            user_id=user.id,
            filename=filename,
            content_bytes=content_bytes,
        )

        table_name = ingest_res["table_name"]
        db_path = ingest_res["db_path"]

        # Run profiling & quality audit
        profiles = profiler.profile_table(db_path, table_name)
        quality_res = auditor.evaluate_table_quality(db_path, table_name)

        # Check existing dataset with same name for this user (replace if exists)
        existing = (
            db.query(Dataset)
            .filter(
                Dataset.user_id == user.id,
                Dataset.name == filename,
            )
            .first()
        )

        if existing:
            db.delete(existing)
            db.commit()

        dataset = Dataset(
            user_id=user.id,
            name=filename,
            duckdb_table_name=table_name,
            row_count=ingest_res["row_count"],
            column_count=ingest_res["column_count"],
            quality_score=quality_res["score"],
            quality_summary=quality_res,
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        # Add column models with profiles and semantic descriptions
        for col_meta in ingest_res["columns"]:
            sanitized = col_meta["sanitized_name"]
            raw_h = col_meta["name"]
            dtype = col_meta["data_type"]

            # Match profile
            col_prof = next((p for p in profiles if p["column_name"] == sanitized), None)
            desc = catalog_builder.infer_column_description(raw_h, dtype)

            column = DatasetColumn(
                dataset_id=dataset.id,
                name=raw_h,
                sanitized_name=sanitized,
                data_type=dtype,
                description=desc,
                profile_stats=col_prof,
            )
            db.add(column)

        db.commit()

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

    return MultiUploadResponse(
        datasets=uploaded_list,
        total_files=len(uploaded_list),
    )
