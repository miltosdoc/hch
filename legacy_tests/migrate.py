import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "webdoc_patients.db"
conn = sqlite3.connect(db_path)
try:
    conn.execute("ALTER TABLE patients ADD COLUMN uploaded_at TEXT;")
    print("Column added successfully!")
except Exception as e:
    print("Migration error:", e)
conn.commit()
conn.close()
