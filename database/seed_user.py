import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()
from db import connect  # noqa: E402

conn = connect()
with conn.cursor() as cur:
    cur.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
        ("Reception Admin", "admin@example.com", generate_password_hash("ChangeMe123!")),
    )
conn.commit()
conn.close()
print("User created")