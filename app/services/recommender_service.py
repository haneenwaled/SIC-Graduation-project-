from sqlalchemy.orm import Session
from app.db.models import Recommendation

def get_top_k_recommendations(db: Session, customer_id: int, k: int = 10):
    return (
        db.query(Recommendation)
        .filter(Recommendation.customer_id == customer_id)
        .order_by(Recommendation.rank.asc())
        .limit(k)
        .all()
    )
