
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.semantic_search import search_evidence

router = APIRouter(
    prefix="/search",
    tags=["Semantic Search"]
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    project_id: int = Field(gt=0)
    top_k: int = Field(default=5, ge=1, le=20)


@router.post("/")
def search_project_evidence(request: SearchRequest):

    try:
        results = search_evidence(
            query=request.query,
            project_id=request.project_id,
            top_k=request.top_k
        )

        if not results:
            return {
                "message": "No sufficiently relevant evidence found.",
                "query": request.query,
                "total_results": 0,
                "results": []
            }

        return {
            "message": "Evidence retrieved successfully.",
            "query": request.query,
            "total_results": len(results),
            "results": results
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Semantic search failed: {str(error)}"
        )
