import sqlite3
import os
from config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(Config.DATABASE_PATH), 'models'), exist_ok=True)
    conn = get_db_connection()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    
    # Check if default outlets exist, if not seed them
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM outlets")
    row = cur.fetchone()
    if row['cnt'] == 0:
        default_outlets = [
            ("Campus Canteen (Meals)", "CAN", "Canteen / Cafeteria", "Counter 1", 3.5),
            ("Quick Bites & Beverages", "BEV", "Beverages & Snacks", "Counter 2", 2.0),
            ("Student Admin & Fee Office", "ADM", "Administrative Services", "Counter 3", 6.0),
            ("Central Library Circulation", "LIB", "Library Services", "Desk A", 2.5),
        ]
        cur.executemany("""
            INSERT INTO outlets (name, code, service_type, counter_number, avg_service_time_mins)
            VALUES (?, ?, ?, ?, ?)
        """, default_outlets)
        conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
