import pytest
import httpx

from app.search.openalex import OpenAlexAdapter
from app.models.schemas import SearchFilters


@pytest.mark.asyncio
async def test_openalex_search():
    adapter = OpenAlexAdapter()
    filters = SearchFilters(limit=3)
    results = await adapter.search("machine learning education", filters)
    assert len(results) > 0
    assert results[0].title
    assert results[0].source.value == "openalex"
