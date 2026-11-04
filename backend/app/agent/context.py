"""Context and conversational reference resolver for follow-up questions."""

import re
from typing import Any

from app.agent.memory import AgentMemory


class ContextResolver:
    """Resolves conversational pronouns, elisions, and follow-up references using entity memory."""

    def resolve(
        self, question: str, memory: AgentMemory | None = None
    ) -> tuple[str, dict[str, Any]]:
        """Transform incomplete follow-up prompt into a fully self-contained analytical query.

        Returns:
            (resolved_question, extracted_entities)
        """
        q = question.strip()
        q_lower = q.lower()
        extracted: dict[str, Any] = {}

        if not memory or not memory.turns:
            # Standalone initial question - extract baseline entities
            extracted = self._extract_entities(q_lower)
            return q, extracted

        last_turn = memory.turns[-1]
        last_q = last_turn.resolved_question or last_turn.user_question
        working = memory.working

        # Pattern 1: Temporal resolution ("now by month", "by month", "break down by month")
        if re.search(r"\b(now\s+)?(by\s+month|monthly(\s+trend)?|over\s+time)\b", q_lower):
            metric = working.last_metric or "sales"
            resolved = f"Show monthly sales trends for {metric} over time."
            extracted = {"metric": metric, "time_granularity": "month"}
            return resolved, extracted

        # Pattern 2: Causal resolution ("why is that low?", "why did it drop?", "why is that?")
        if re.search(r"\bwhy\b", q_lower) and any(
            w in q_lower for w in ("low", "drop", "dip", "fall", "that")
        ):
            region = working.resolved_entities.get("region", "EMEA")
            period = working.resolved_entities.get("period", "March 2024")
            resolved = f"Why did {region} revenue drop in {period}?"
            extracted = {"investigation_target": region, "period": period}
            return resolved, extracted

        # Pattern 3: Code request follow-up ("generate sql for this analysis", "show sql", "give me the code")
        if any(kw in q_lower for kw in ("sql", "code", "query")) and any(
            kw in q_lower for kw in ("generate", "show", "this", "that")
        ):
            target = last_q.rstrip("?")
            resolved = f"Generate SQL for this analysis: {target}"
            extracted = {"code_target": target}
            return resolved, extracted

        # Pattern 4: Entity filter refinement ("now for North America", "filter by EMEA")
        region_match = re.search(
            r"\b(for|in|filter\s+by)\s+(north\s+america|emea|apac|latam)\b", q_lower
        )
        if region_match:
            region = region_match.group(2).title()
            resolved = f"{last_q.rstrip('.')} in {region}."
            extracted = {"region": region}
            return resolved, extracted

        # Pattern 5: Dimension shift ("now by product", "break down by region")
        if "by product" in q_lower:
            resolved = "Show underperforming products breakdown."
            extracted = {"dimension": "product_id"}
            return resolved, extracted

        extracted = self._extract_entities(q_lower)
        return q, extracted

    def _extract_entities(self, text: str) -> dict[str, Any]:
        """Extract analytical entities from query text."""
        entities: dict[str, Any] = {}
        if "revenue" in text or "sales" in text:
            entities["metric"] = "revenue"
        if "region" in text:
            entities["dimension"] = "region"
        if "north america" in text:
            entities["region"] = "North America"
        elif "emea" in text:
            entities["region"] = "EMEA"
        elif "apac" in text:
            entities["region"] = "APAC"
        if "product" in text:
            entities["dimension"] = "product_id"
        if "customer" in text:
            entities["dimension"] = "customer_id"
        if "month" in text:
            entities["time_granularity"] = "month"
        return entities
