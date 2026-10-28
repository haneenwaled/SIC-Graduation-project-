import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Retail AI Backend"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/retail_db"
    LAPSE_MODEL_PATH: str = "artifacts/lapse_model/selected_customer_lapse_model.joblib"
    CSV_RECOMMENDATIONS_PATH: str = "artifacts/recommender/product_recommendations_top10.csv"
    RISK_THRESHOLD: float = 0.30
    GEMINI_API_KEY: str = ""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()