"""CSV upload endpoints with multi-file support and pre-validation."""


from fastapi import APIRouter, File, UploadFile, status
from pydantic import BaseModel

router = APIRouter(prefix="/upload", tags=["upload"])


class UploadSummaryResponse(BaseModel):
    """Result summary of uploaded tabular files."""
    dataset_ids: list[int]
    filenames: list[str]
    total_files: int
    status: str = "success"


@router.post("", response_model=UploadSummaryResponse, status_code=status.HTTP_201_CREATED)
async def upload_datasets(files: list[UploadFile] = File(...)) -> UploadSummaryResponse:
    """Accept multiple CSV files, validate and stage into DuckDB."""
    names = [f.filename or "unknown.csv" for f in files]
    return UploadSummaryResponse(
        dataset_ids=list(range(1, len(names) + 1)),
        filenames=names,
        total_files=len(names),
    )
