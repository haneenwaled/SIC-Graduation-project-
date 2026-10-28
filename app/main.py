from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.v1.endpoints import lapse, recommendations, rag
from app.services.rag_service import rag_service
from app.db.session import engine
from app.db import models

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Pre-load FAISS index and embedding model into RAM
    print("Pre-loading RAG Engine and FAISS Vector Store...")
    try:
        rag_service._get_engine()
        print("RAG Engine pre-load complete. Backend ready!")
    except Exception as e:
        print(f"Warning during RAG pre-load: {e}")
    yield

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Retail AI Backend", lifespan=lifespan)

app.include_router(recommendations.router, prefix="/api/v1", tags=["Recommendations"])
app.include_router(lapse.router, prefix="/api/v1", tags=["Lapse Prediction"])
app.include_router(rag.router, prefix="/api/v1", tags=["RAG Assistant"])

@app.get("/health")
def health_check():
    return {"status": "healthy"}