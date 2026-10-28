from sqlalchemy import Column, Integer, String, Float, Date
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Recommendation(Base):
    __tablename__ = "recommendations"

    customer_id = Column(Integer, primary_key=True, index=True)
    rank = Column(Integer, primary_key=True)
    stock_code = Column(String, index=True)
    product_name = Column(String)
    recommendation_score = Column(Float)
    median_unit_price = Column(Float)
    median_quantity = Column(Float)
    estimated_basket_value_gbp = Column(Float)
    as_of_date = Column(String)