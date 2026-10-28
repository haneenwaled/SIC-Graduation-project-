from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.recommendation import RecommendationResponse
from app.db.session import get_db
from app.services.recommender_service import get_top_k_recommendations

router = APIRouter()

@router.get("/recommendations/{customer_id}", response_model=RecommendationResponse)
def get_recommendations(customer_id: int, db: Session = Depends(get_db)):
    recs = get_top_k_recommendations(db, customer_id=customer_id)
    if not recs:
        raise HTTPException(status_code=404, detail="No recommendations found for this customer.")
    
    return {
        "customer_id": customer_id,
        "recommendations": recs
    }