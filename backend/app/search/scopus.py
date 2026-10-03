from app.models.schemas import Paper, SearchFilters


class ScopusAdapter:
    """Stub para integração futura com Elsevier Scopus API."""

    name = "scopus"

    async def search(self, query: str, filters: SearchFilters) -> list[Paper]:
        if not self._is_configured():
            return []
        return []

    async def get_by_id(self, paper_id: str) -> Paper | None:
        return None

    def _is_configured(self) -> bool:
        from app.config import settings

        return bool(settings.scopus_api_key)
