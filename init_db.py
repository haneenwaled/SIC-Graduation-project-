import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from app.config import settings

# Parse connection details
db_url = settings.DATABASE_URL.replace("postgresql://", "")
user_pass, host_port_db = db_url.split("@")
user, password = user_pass.split(":")
host_port, _ = host_port_db.split("/")
host, port = host_port.split(":")

try:
    conn = psycopg2.connect(
        dbname="postgres",
        user=user,
        password=password,
        host=host,
        port=port
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE retail_db;")
    print("Database 'retail_db' created successfully!")
    cursor.close()
    conn.close()
except Exception as e:
    print("Database setup status/message:", e)