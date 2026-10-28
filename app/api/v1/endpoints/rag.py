from fastapi import APIRouter, HTTPException
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse
from app.services.rag_service import rag_service

router = APIRouter()

@router.post("/rag-chat", response_model=RAGQueryResponse)
def rag_chat(request: RAGQueryRequest):
    try:
        res = rag_service.query(request.question)
        return {
            "question": request.question,
            "answer": res.get("answer", "")
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"RAG Engine Error ({type(e).__name__}): {str(e)}"
        )