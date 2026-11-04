"""Dataset metadata, column profile, quality score, relationship graph, and metrics endpoints."""

from typing import Any

import duckdb
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError
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
    expression: str = Field(..., description="SQL aggregation expression, e.g. 'SUM(quantity * unit_price)'")
    description: str | None = None


class MetricResponse(BaseModel):
    id: int
    name: str
    expression: str
    description: str | None


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

    existing_metric = db.query(MetricDefinition).filter(
        MetricDefinition.user_id == user.id,
        MetricDefinition.name == req.name,
    ).first()

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

    # Drop from DuckDB
    try:
        con = duckdb.connect(db_path)
        con.execute(f'DROP TABLE IF EXISTS "{table_name}";')
        con.close()
    except Exception:
        pass

    db.delete(dataset)
    db.commit()
    return None
