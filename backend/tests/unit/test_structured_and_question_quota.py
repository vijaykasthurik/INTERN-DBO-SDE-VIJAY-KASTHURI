from unittest.mock import AsyncMock

import pytest

from app.llm.base import LLMResponse
from app.llm.structured import NarrativeDraft, complete_json
from app.llm.pool import _USER_SHARED_HOURLY_USAGE, _USER_SHARED_ANALYSES, check_and_record_shared_quota


def test_quota_charges_question_once_without_bypassing_limit(monkeypatch):
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "shared_pool_hourly_limit", 2)
    _USER_SHARED_HOURLY_USAGE.clear()
    _USER_SHARED_ANALYSES.clear()
    assert check_and_record_shared_quota(777, "first") == (True, 1)
    assert check_and_record_shared_quota(777, "first") == (True, 1)
    assert check_and_record_shared_quota(777, "second") == (True, 0)
    assert check_and_record_shared_quota(777, "third") == (False, 0)
    assert check_and_record_shared_quota(777, "second") == (True, 0)


@pytest.mark.asyncio
async def test_schema_repair_preserves_one_logical_analysis():
    router = AsyncMock()
    router.complete.side_effect = [LLMResponse(content="bad JSON"), LLMResponse(content='```json\n{"direct_answer":"Recorded result", "business_insight":"From data", "how_i_got_this":"SELECT", "suggested_followups":[]}\n```')]
    result = await complete_json(router, "Read evidence", NarrativeDraft, analysis_id="same-analysis")
    assert result.direct_answer == "Recorded result"
    assert router.complete.await_count == 2
    assert all(call.kwargs["analysis_id"] == "same-analysis" for call in router.complete.call_args_list)
