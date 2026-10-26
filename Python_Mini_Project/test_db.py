
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

user = os.getenv("DB_USER")

print("Environment file found:", env_path.exists())
print("MySQL username:", repr(user))
print("Database name:", repr(os.getenv("DB_NAME")))

try:
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=user,
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

    print("MySQL connection successful!")

    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    print("Tables:", cursor.fetchall())

    cursor.close()
    connection.close()

except mysql.connector.Error as error:
    print("MySQL connection failed:", error)


