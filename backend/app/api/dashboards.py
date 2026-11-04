"""Dashboard generation, layout customization, and retrieval endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.data.ingestion import DataIngestionPipeline
from app.db.models import User
from app.deps import get_current_user_optional
from app.tools.dashboard_tool import DashboardTool

router = APIRouter(prefix="/dashboards", tags=["dashboards"])
_DASHBOARDS_STORE: dict[str, dict[str, Any]] = {}
_TOOL = DashboardTool()


class GenerateDashboardRequest(BaseModel):
    """Dashboard creation payload."""
    title: str | None = "Executive Sales & Operations Overview"


class DashboardResponse(BaseModel):
    """Auto-generated dashboard layout and widget specifications."""
    id: str
    title: str
    widget_count: int = 5
    widgets: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/generate", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def generate_dashboard(
    req: GenerateDashboardRequest | None = None,
    current_user: User | None = Depends(get_current_user_optional),
) -> DashboardResponse:
    """Analyze current dataset catalog and generate 4-6 responsive KPI/trend widgets from real DuckDB data."""
    title = req.title if req and req.title else "Executive Sales & Operations Overview"
    db_path = None
    if current_user:
        pipeline = DataIngestionPipeline()
        db_path = pipeline.get_user_db_path(current_user.id)

    dashboard_data = _TOOL.generate_dashboard(title=title, db_path=db_path)
    _DASHBOARDS_STORE[dashboard_data["id"]] = dashboard_data

    return DashboardResponse(
        id=dashboard_data["id"],
        title=dashboard_data["title"],
        widget_count=dashboard_data["widget_count"],
        widgets=dashboard_data["widgets"],
    )


@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(dashboard_id: str) -> DashboardResponse:
    """Retrieve saved dashboard layout and widgets by ID."""
    dash = _DASHBOARDS_STORE.get(dashboard_id)
    if not dash:
        dash = _TOOL.generate_dashboard()
        dash["id"] = dashboard_id
        _DASHBOARDS_STORE[dashboard_id] = dash

    return DashboardResponse(
        id=dash["id"],
        title=dash["title"],
        widget_count=dash["widget_count"],
        widgets=dash["widgets"],
    )
