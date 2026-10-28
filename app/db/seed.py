import pandas as pd
from app.config import settings
from app.db.session import engine

def seed_recommendations():
    print(f"Loading CSV data from {settings.CSV_RECOMMENDATIONS_PATH}...")
    df = pd.read_csv(settings.CSV_RECOMMENDATIONS_PATH)
    print("Writing records to PostgreSQL table 'recommendations'...")
    df.to_sql("recommendations", engine, if_exists="replace", index=False)
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_recommendations()