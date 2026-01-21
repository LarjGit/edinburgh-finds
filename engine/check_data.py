import sqlite3
import os

# Adjust path to where the Next.js app keeps the SQLite DB
DB_PATH = os.path.join(os.path.dirname(__file__), '../web/dev.db')

def check_data():
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at: {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM Entity")
        count = cursor.fetchone()[0]
        
        print(f"Listing count: {count}")
        
        if count > 0:
            cursor.execute("SELECT entity_name, entityTypeId FROM Entity LIMIT 3")
            print("Sample data:")
            for row in cursor.fetchall():
                print(f" - {row[0]} ({row[1]})")
        
        conn.close()
    except Exception as e:
        print(f"Error reading database: {e}")

if __name__ == "__main__":
    check_data()
