"""Shared ingestion and metadata persistence for upload and replacement."""
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.data.catalog import SemanticCatalogBuilder
from app.data.ingestion import DataIngestionPipeline
from app.data.lifecycle import invalidate_dataset
from app.data.profiler import DatasetProfiler
from app.data.quality import QualityAuditor
from app.db.models import Dataset, DatasetColumn, User


def persist_dataset(db: Session, user: User, filename: str, content: bytes, existing: Dataset | None = None, source_filename: str | None = None) -> Dataset:
    pipeline = DataIngestionPipeline()
    if existing is None:
        existing = db.query(Dataset).filter(Dataset.user_id == user.id, Dataset.name == filename).first()
    table = existing.duckdb_table_name if existing else pipeline.sanitize_table_name(filename)
    collision = db.query(Dataset).filter(Dataset.user_id == user.id, Dataset.duckdb_table_name == table).first()
    if collision is not None and (existing is None or collision.id != existing.id):
        raise ValidationError("Another filename resolves to the same table identifier. Rename the file before uploading.")
    result = pipeline.ingest_csv(user.id, f"{table}.csv", content)
    profiles = DatasetProfiler().profile_table(result["db_path"], table)
    quality = QualityAuditor().evaluate_table_quality(result["db_path"], table)
    catalog = SemanticCatalogBuilder()
    dataset = existing or Dataset(user_id=user.id, name=filename, duckdb_table_name=table)
    if existing:
        invalidate_dataset(db, user.id, existing.id)
        for column in list(existing.columns):
            db.delete(column)
        for metric in list(existing.metrics):
            db.delete(metric)
    dataset.source_filename = source_filename or dataset.source_filename or filename
    db.add(dataset)
    dataset.row_count = result["row_count"]
    dataset.column_count = result["column_count"]
    dataset.quality_score = quality["score"]
    dataset.quality_summary = quality
    db.flush()
    for column in result["columns"]:
        name = column["sanitized_name"]
        db.add(DatasetColumn(dataset_id=dataset.id, name=column["name"], sanitized_name=name, data_type=column["data_type"], description=catalog.infer_column_description(column["name"], column["data_type"]), profile_stats=next((profile for profile in profiles if profile["column_name"] == name), None)))
    db.commit()
    db.refresh(dataset)
    return dataset
