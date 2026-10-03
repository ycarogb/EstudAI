import hashlib
import re
import unicodedata
from typing import Protocol

from app.models.schemas import Paper, SearchFilters


class SearchAdapter(Protocol):
    name: str

    async def search(self, query: str, filters: SearchFilters) -> list[Paper]: ...

    async def get_by_id(self, paper_id: str) -> Paper | None: ...


def normalize_title(title: str) -> str:
    text = unicodedata.normalize("NFKD", title.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def make_paper_id(source: str, identifier: str) -> str:
    raw = f"{source}:{identifier}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
