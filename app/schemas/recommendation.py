from pydantic import BaseModel
from typing import List

class RecommendationItem(BaseModel):
    rank: int
    stock_code: str
    product_name: str
    estimated_basket_value_gbp: float

    class Config:
        from_attributes = True

class RecommendationResponse(BaseModel):
    customer_id: int
    recommendations: List[RecommendationItem]