"""Dataset metadata, column profile, quality score, relationship graph, and metrics endpoints."""

from typing import Any, Literal

import duckdb
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.data.ingestion import DataIngestionPipeline
from app.data.relationships import RelationshipDetector
from app.db.models import Dataset, MetricDefinition, User
from app.db.session import get_db
from app.deps import get_current_user

router = APIRouter(prefix="/datasets", tags=["datasets"])


class ColumnDetail(BaseModel):
    id: int
    name: str
    sanitized_name: str
    data_type: str
    description: str | None
    profile_stats: dict[str, Any] | None


class DatasetDetailResponse(BaseModel):
    id: int
    name: str
    table_name: str
    row_count: int
    column_count: int
    quality_score: float
    quality_summary: dict[str, Any] | None
    columns: list[ColumnDetail]


class UpdateMetricRequest(BaseModel):
    name: str = Field(..., description="Metric identifier, e.g. 'gross_revenue'")
    expression: str = Field(
        ..., description="SQL aggregation expression, e.g. 'SUM(quantity * unit_price)'"
    )
    description: str | None = None


class MetricResponse(BaseModel):
    id: int
    name: str
    expression: str
    description: str | None


@router.get("/{dataset_id}/metrics", response_model=list[MetricResponse])
async def list_dataset_metrics(
    dataset_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MetricResponse]:
    """List persisted metric definitions owned by the requested dataset and tenant."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == user.id).first()
    if not dataset:
        raise NotFoundError(f"Dataset with ID {dataset_id} not found")
    return [MetricResponse(id=metric.id, name=metric.name, expression=metric.expression, description=metric.description) for metric in dataset.metrics]


@router.get("", response_model=list[DatasetDetailResponse])
async def list_datasets(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DatasetDetailResponse]:
    """List all registered datasets for current user."""
    datasets = db.query(Dataset).filter(Dataset.user_id == user.id).all()
    results: list[DatasetDetailResponse] = []
    for d in datasets:
        cols = [
            ColumnDetail(
                id=c.id,
                name=c.name,
                sanitized_name=c.sanitized_name,
                data_type=c.data_type,
                description=c.description,
                profile_stats=c.profile_stats,
            )
            for c in d.columns
        ]
        results.append(
            DatasetDetailResponse(
                id=d.id,
                name=d.name,
                table_name=d.duckdb_table_name,
                row_count=d.row_count,
                column_count=d.column_count,
                quality_score=d.quality_score,
                quality_summary=d.quality_summary,
                columns=cols,
            )
        )
    return results


@router.get("/relationships")
async def get_relationships(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Compute and return relationship graph across all uploaded tables for the current user."""
    datasets = db.query(Dataset).filter(Dataset.user_id == user.id).all()
    if len(datasets) < 2:
        return {"relationships": [], "total_edges": 0}

    pipeline = DataIngestionPipeline()
    db_path = pipeline.get_user_db_path(user.id)
    table_names = [d.duckdb_table_name for d in datasets]

    detector = RelationshipDetector()
    edges = detector.detect_table_relationships(db_path, table_names)

    return {"relationships": edges, "total_edges": len(edges)}


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
async def get_dataset(
    dataset_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetDetailResponse:
    """Retrieve column profiles, semantic descriptions and quality scores for specific dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise NotFoundError(f"Dataset with ID {dataset_id} not found")

    if dataset.user_id != user.id:
        raise PermissionDeniedError("Access to this dataset is denied")

    cols = [
        ColumnDetail(
            id=c.id,
            name=c.name,
            sanitized_name=c.sanitized_name,
            data_type=c.data_type,
            description=c.description,
            profile_stats=c.profile_stats,
        )
        for c in dataset.columns
    ]
    return DatasetDetailResponse(
        id=dataset.id,
        name=dataset.name,
        table_name=dataset.duckdb_table_name,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        quality_score=dataset.quality_score,
        quality_summary=dataset.quality_summary,
        columns=cols,
    )


@router.get("/{dataset_id}/rows")
async def get_dataset_rows(
    dataset_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    q: str = Query(default="", max_length=500),
    sort: str | None = None,
    direction: Literal["asc", "desc"] = "asc",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return one bounded, server-paginated page of real rows from the tenant warehouse."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == user.id).first()
    if not dataset:
        raise NotFoundError(f"Dataset with ID {dataset_id} not found")
    pipeline = DataIngestionPipeline()
    con = duckdb.connect(pipeline.get_user_db_path(user.id), read_only=True)
    try:
        schema = con.execute(f'DESCRIBE "{dataset.duckdb_table_name}"').fetchall()
        columns = [str(column[0]) for column in schema]
        if sort is not None and sort not in columns:
            raise ValidationError("Sort column is not part of this dataset.")
        predicate = " OR ".join(f'contains(lower(CAST("{column}" AS VARCHAR)), lower(?))' for column in columns)
        where = f" WHERE ({predicate})" if q else ""
        parameters: list[Any] = [q] * len(columns) if q else []
        count_result = con.execute(f'SELECT COUNT(*) FROM "{dataset.duckdb_table_name}"{where}', parameters).fetchone()
        total_rows = int(count_result[0]) if count_result else 0
        order = f' ORDER BY "{sort}" {direction.upper()} NULLS LAST' if sort else ""
        result = con.execute(f'SELECT * FROM "{dataset.duckdb_table_name}"{where}{order} LIMIT ? OFFSET ?', [*parameters, limit, offset])
        rows = result.fetchall()
    finally:
        con.close()
    return {
        "columns": columns,
        "rows": [dict(zip(columns, row, strict=True)) for row in rows],
        "offset": offset,
        "limit": limit,
        "total_rows": total_rows,
        "column_types": {str(column[0]): str(column[1]) for column in schema},
        "column_null_counts": {column.sanitized_name: (column.profile_stats or {}).get("null_count") for column in dataset.columns},
    }


@router.patch("/{dataset_id}/metrics", response_model=MetricResponse)
async def update_dataset_metric(
    dataset_id: int,
    req: UpdateMetricRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MetricResponse:
    """Create or update a business metric definition for this dataset or user."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == user.id).first()
    if not dataset:
        raise NotFoundError(f"Dataset with ID {dataset_id} not found")

    existing_metric = (
        db.query(MetricDefinition)
        .filter(
            MetricDefinition.user_id == user.id,
            MetricDefinition.name == req.name,
        )
        .first()
    )

    if existing_metric:
        existing_metric.expression = req.expression
        existing_metric.description = req.description
        existing_metric.dataset_id = dataset.id
        metric = existing_metric
    else:
        metric = MetricDefinition(
            user_id=user.id,
            dataset_id=dataset.id,
            name=req.name,
            expression=req.expression,
            description=req.description,
        )
        db.add(metric)

    db.commit()
    db.refresh(metric)

    return MetricResponse(
        id=metric.id,
        name=metric.name,
        expression=metric.expression,
        description=metric.description,
    )


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove dataset from SQLite metadata and drop table from user's DuckDB."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise NotFoundError(f"Dataset with ID {dataset_id} not found")

    if dataset.user_id != user.id:
        raise PermissionDeniedError("Access to this dataset is denied")

    pipeline = DataIngestionPipeline()
    db_path = pipeline.get_user_db_path(user.id)
    table_name = dataset.duckdb_table_name

    # Drop from the analytical database before committing metadata removal.
    con = duckdb.connect(db_path)
    try:
        con.execute(f'DROP TABLE IF EXISTS "{table_name}";')
    finally:
        con.close()

    from app.data.lifecycle import invalidate_dataset
    invalidate_dataset(db, user.id, dataset_id)
    db.delete(dataset)
    db.commit()
    return None


class RenameDatasetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


@router.patch("/{dataset_id}", response_model=DatasetDetailResponse)
async def rename_dataset(dataset_id: int, body: RenameDatasetRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DatasetDetailResponse:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == user.id).first()
    if not dataset:
        raise NotFoundError("Dataset not found")
    name = body.name.strip()
    if not name:
        raise ValidationError("Dataset name cannot be blank.")
    duplicate = db.query(Dataset).filter(Dataset.user_id == user.id, Dataset.name == name, Dataset.id != dataset_id).first()
    if duplicate:
        raise ValidationError("A dataset with this name already exists.")
    dataset.name = name
    db.commit()
    return await get_dataset(dataset_id, user, db)


@router.post("/{dataset_id}/replace", response_model=DatasetDetailResponse)
async def replace_dataset(dataset_id: int, file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DatasetDetailResponse:
    from app.config import get_settings
    from app.data.persistence import persist_dataset
    from app.data.workbook import expand_upload
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == user.id).first()
    if not dataset:
        raise NotFoundError("Dataset not found")
    expanded = expand_upload(file.filename or "replacement.csv", await file.read(), get_settings().max_upload_mb)
    if len(expanded) != 1:
        raise ValidationError("Replace accepts one table. Upload a single-sheet workbook or CSV.")
    persist_dataset(db, user, dataset.name, expanded[0][1], existing=dataset)
    return await get_dataset(dataset_id, user, db)
