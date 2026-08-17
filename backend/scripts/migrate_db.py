import sqlite3
import os

db_path = "research_platform.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(contradictions)")
    cols = [info[1] for info in cursor.fetchall()]
    print("Current columns in contradictions:", cols)
    if "contradiction_category" not in cols:
        print("Adding contradiction_category column...")
        cursor.execute("ALTER TABLE contradictions ADD COLUMN contradiction_category VARCHAR(50) DEFAULT 'DIRECT_CONTRADICTION'")
        conn.commit()
        print("Successfully added contradiction_category column!")
    else:
        print("contradiction_category column already exists.")
    conn.close()
else:
    print(f"Database {db_path} not found.")
