import os
import joblib
import pandas as pd
from app.config import settings
from app.schemas.lapse import LapsePredictionRequest

EXPECTED_FEATURES = [
    "recency_days",
    "frequency_orders",
    "monetary",
    "average_order_value",
    "average_basket_quantity",
    "distinct_products",
    "tenure_days",
    "average_days_between_orders",
    "orders_last_30d",
    "orders_last_90d",
    "orders_last_180d",
    "spend_last_30d",
    "spend_last_90d",
    "spend_last_180d",
    "cancellation_count",
    "cancellation_value",
    "cancellation_rate",
    "country"
]

class LapseService:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        model_path = settings.LAPSE_MODEL_PATH
        
        # Check fallback locations if missing from primary artifacts path
        if not os.path.exists(model_path):
            alternatives = [
                "artifacts/lapse_model/selected_customer_lapse_model.joblib",
                "customer_lapse_outputs/selected_customer_lapse_model.joblib",
                "selected_customer_lapse_model.joblib"
            ]
            for alt in alternatives:
                if os.path.exists(alt):
                    model_path = alt
                    break

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model file 'selected_customer_lapse_model.joblib' not found. "
                f"Ensure it exists in artifacts/lapse_model/"
            )
        
        self.model = joblib.load(model_path)

    def predict_risk(self, request_data: LapsePredictionRequest) -> dict:
        if self.model is None:
            self._load_model()

        data = request_data.model_dump()
        customer_id = data.pop("customer_id")

        # Build single-row DataFrame with exact feature columns
        df = pd.DataFrame([data])[EXPECTED_FEATURES]

        # Calculate prediction probability
        prob_array = self.model.predict_proba(df)
        prob = float(prob_array[0][1])

        # Categorize risk level
        if prob >= settings.RISK_THRESHOLD:
            risk_category = "High"
        elif prob >= settings.RISK_THRESHOLD * 0.60:
            risk_category = "Medium"
        else:
            risk_category = "Low"

        return {
            "customer_id": customer_id,
            "lapse_probability": round(prob, 4),
            "risk_category": risk_category,
        }

lapse_model_runner = LapseService()