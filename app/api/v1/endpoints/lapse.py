from fastapi import APIRouter, HTTPException
from app.schemas.lapse import LapsePredictionRequest, LapsePredictionResponse
from app.services.lapse_service import lapse_model_runner

router = APIRouter()

@router.post("/predict-lapse", response_model=LapsePredictionResponse)
def predict_customer_lapse(request: LapsePredictionRequest):
    try:
        return lapse_model_runner.predict_risk(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lapse Prediction Error ({type(e).__name__}): {str(e)}"
        )