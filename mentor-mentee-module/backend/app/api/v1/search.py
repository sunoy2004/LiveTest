from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_search_service
from app.schemas.search import SearchResult, SearchRole
from app.services.search_service import SearchService

router = APIRouter()


@router.get("", response_model=list[SearchResult])
async def search(
    svc: Annotated[SearchService, Depends(get_search_service)],
    q: Annotated[str, Query(..., min_length=1, max_length=128, description="Search term")],
    role: Annotated[SearchRole, Query()] = SearchRole.mentor,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[SearchResult]:
    return await svc.search(q=q, role=role, limit=limit)

