import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application settings loaded from environment variables."""

    SECRET_KEY = os.getenv("FLASK_SECRET_KEY") or os.urandom(32)
    MYSQL_HOST = os.getenv("DB_HOST", "localhost")
    MYSQL_PORT = os.getenv("DB_PORT", "3306")
    MYSQL_USER = os.getenv("DB_USERNAME") or os.getenv("DB_USER", "")
    MYSQL_PASSWORD = os.getenv("DB_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("DB_NAME", "")


def get_db_connection():
    """Open a MySQL connection using the settings loaded from .env."""
    try:
        port = int(Config.MYSQL_PORT)
    except (TypeError, ValueError):
        raise ValueError("DB_PORT must be a valid integer.") from None
    if port < 1 or port > 65535:
        raise ValueError("DB_PORT must be between 1 and 65535.")

    if not Config.MYSQL_HOST or not Config.MYSQL_USER or not Config.MYSQL_DATABASE:
        raise ValueError("Set DB_HOST, DB_USERNAME, and DB_NAME in .env.")

    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        port=port,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE,
    )
