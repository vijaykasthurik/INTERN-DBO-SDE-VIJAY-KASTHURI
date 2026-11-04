"""Dashboard generation, layout customization, and retrieval endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.data.ingestion import DataIngestionPipeline
from app.db.models import Dataset, User
from app.db.session import get_db
from app.deps import get_current_user
from app.tools.dashboard_tool import DashboardTool

router = APIRouter(prefix="/dashboards", tags=["dashboards"])
_DASHBOARDS_STORE: dict[str, tuple[int, dict[str, Any], set[int]]] = {}
_TOOL = DashboardTool()


class GenerateDashboardRequest(BaseModel):
    """Dashboard creation payload."""
    title: str | None = "Executive Sales & Operations Overview"
    scope: str = "combined"


class DashboardResponse(BaseModel):
    """Auto-generated dashboard layout and widget specifications."""
    id: str
    title: str
    widget_count: int = 5
    widgets: list[dict[str, Any]] = Field(default_factory=list)
    scope: str = "combined"
    scope_label: str = "All uploaded files"
    relationships_used: list[str] = Field(default_factory=list)
    explanation: str = ""


def invalidate_dataset_dashboards(user_id: int, dataset_id: int) -> None:
    """Discard in-memory dashboards that include a removed dataset."""
    for key, (owner_id, _data, dataset_ids) in list(_DASHBOARDS_STORE.items()):
        if owner_id == user_id and (dataset_id in dataset_ids or not dataset_ids):
            del _DASHBOARDS_STORE[key]


@router.post("/generate", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def generate_dashboard(
    req: GenerateDashboardRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    """Analyze the requested owned dataset scope using live read-only DuckDB queries."""
    title = req.title if req and req.title else "Executive Sales & Operations Overview"
    datasets = db.query(Dataset).filter(Dataset.user_id == current_user.id).all()
    if not datasets:
        raise HTTPException(status_code=409, detail="Upload a dataset before generating a dashboard.")
    scope = req.scope if req else "combined"
    selected = None
    if scope != "combined":
        try:
            selected_id = int(scope)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Dashboard scope must be 'combined' or a dataset ID.") from exc
        selected = next((dataset for dataset in datasets if dataset.id == selected_id), None)
        if not selected:
            raise HTTPException(status_code=404, detail="The selected dataset is no longer available.")
    pipeline = DataIngestionPipeline()
    dashboard_data = _TOOL.generate_dashboard(
        title=title, db_path=pipeline.get_user_db_path(current_user.id),
        scope_table=selected.duckdb_table_name if selected else None,
    )
    dataset_ids = {selected.id} if selected else {dataset.id for dataset in datasets}
    _DASHBOARDS_STORE[dashboard_data["id"]] = (current_user.id, dashboard_data, dataset_ids)

    return DashboardResponse(
        id=dashboard_data["id"],
        title=dashboard_data["title"],
        widget_count=dashboard_data["widget_count"],
        widgets=dashboard_data["widgets"],
        scope=dashboard_data["scope"], scope_label=dashboard_data["scope_label"],
        relationships_used=dashboard_data["relationships_used"], explanation=dashboard_data["explanation"],
    )


@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: str,
    current_user: User = Depends(get_current_user),
) -> DashboardResponse:
    """Retrieve saved dashboard layout and widgets by ID."""
    stored = _DASHBOARDS_STORE.get(dashboard_id)
    if not stored or stored[0] != current_user.id:
        from app.core.errors import NotFoundError
        raise NotFoundError(f"Dashboard '{dashboard_id}' not found")
    dash = stored[1]

    return DashboardResponse(
        id=dash["id"],
        title=dash["title"],
        widget_count=dash["widget_count"],
        widgets=dash["widgets"],
        scope=dash["scope"], scope_label=dash["scope_label"],
        relationships_used=dash["relationships_used"], explanation=dash["explanation"],
    )
