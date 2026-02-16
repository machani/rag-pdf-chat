import sqlite3
import os

DB_FILE = "data/chat_history.db"

if not os.path.exists(DB_FILE):
    print("Database file does not exist.")
else:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT count(*) FROM messages")
        count = c.fetchone()[0]
        print(f"Total messages: {count}")
        
        c.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 5")
        rows = c.fetchall()
        print("Last 5 messages:")
        for row in rows:
            print(row)
        conn.close()
    except Exception as e:
        print(f"Error reading database: {e}")
