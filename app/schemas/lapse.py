from pydantic import BaseModel, Field

class LapsePredictionRequest(BaseModel):
    customer_id: int = Field(..., example=12346)
    recency_days: int = Field(..., example=120)
    frequency_orders: int = Field(..., example=5)
    monetary: float = Field(..., example=450.0)
    average_order_value: float = Field(..., example=90.0)
    average_basket_quantity: float = Field(..., example=12.5)
    distinct_products: int = Field(..., example=15)
    tenure_days: int = Field(..., example=365)
    average_days_between_orders: float = Field(..., example=30.0)
    orders_last_30d: int = Field(..., example=0)
    orders_last_90d: int = Field(..., example=0)
    orders_last_180d: int = Field(..., example=2)
    spend_last_30d: float = Field(..., example=0.0)
    spend_last_90d: float = Field(..., example=0.0)
    spend_last_180d: float = Field(..., example=150.0)
    cancellation_count: int = Field(..., example=0)
    cancellation_value: float = Field(..., example=0.0)
    cancellation_rate: float = Field(..., example=0.0)
    country: str = Field(..., example="United Kingdom")

class LapsePredictionResponse(BaseModel):
    customer_id: int
    lapse_probability: float
    risk_category: str