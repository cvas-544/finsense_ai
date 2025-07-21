import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Extract DB credentials from environment
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")  # Default PostgreSQL port

def get_db_connection():
    """
    Establish and return a connection to the PostgreSQL RDS instance.
    Make sure to close the connection manually after use.
    """
    try:
        print("Connecting with:", DB_HOST, DB_NAME, DB_USER, DB_PORT)
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print("❌ Failed to connect to DB:", e)
        raise