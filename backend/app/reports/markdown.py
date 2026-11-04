"""Markdown Report exporter."""

from typing import Any


class MarkdownReportExporter:
    """Renders structured GitHub-Flavored Markdown reports with embedded tables."""

    def render_markdown(self, report_data: dict[str, Any]) -> str:
        """Convert report dictionary into Markdown."""
        return f"# {report_data.get('title', 'Lumen Report')}\n\n{report_data.get('summary', '')}\n"
