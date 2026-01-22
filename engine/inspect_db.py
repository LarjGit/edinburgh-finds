import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '../web/dev.db')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("Tables:")
for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';"):
    print(row[0])

print("\nEntity Columns:")
for row in cursor.execute("PRAGMA table_info(Entity);"):
    print(row[1], row[2])

conn.close()

