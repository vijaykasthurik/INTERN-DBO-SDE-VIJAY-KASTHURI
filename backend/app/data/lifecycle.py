"""Invalidate all analytical artifacts that depend on a changed dataset."""
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import CacheEntry, ChatSession, DashboardOrder, ReportArtifact


def invalidate_dataset(db: Session, user_id: int, dataset_id: int) -> None:
    from app.api.chat import _AGENT_ENGINE, _SESSION_MEMORIES
    from app.api.dashboards import invalidate_dataset_dashboards
    from app.api.reports import REPORTS_DIR

    artifacts = db.query(ReportArtifact).filter(ReportArtifact.user_id == user_id).all()
    for artifact in artifacts:
        if not artifact.source_dataset_ids or dataset_id in artifact.source_dataset_ids:
            path = Path(REPORTS_DIR) / Path(artifact.filename).name
            path.unlink(missing_ok=True)
            db.delete(artifact)
    db.query(CacheEntry).delete(synchronize_session=False)
    db.query(DashboardOrder).filter(DashboardOrder.user_id == user_id, DashboardOrder.scope == str(dataset_id)).delete(synchronize_session=False)
    for session in db.query(ChatSession).filter(ChatSession.user_id == user_id):
        _SESSION_MEMORIES.pop(session.id, None)
    _AGENT_ENGINE.cache._store.clear()
    invalidate_dataset_dashboards(user_id, dataset_id)
