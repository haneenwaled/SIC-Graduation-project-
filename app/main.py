from fastapi import FastAPI
from app.api.v1.endpoints import lapse, recommendations
from app.db.session import engine
from app.db import models

# Auto-create tables in PostgreSQL
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Retail AI Backend")

app.include_router(recommendations.router, prefix="/api/v1", tags=["Recommendations"])
app.include_router(lapse.router, prefix="/api/v1", tags=["Lapse Prediction"])

@app.get("/health")
def health_check():
    return {"status": "healthy"}