import sqlite3
import os
import json
from datetime import datetime

DB_FILE = "data/chat_history.db"

def init_db():
    """Initialize the SQLite database and perform migrations if necessary."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. Create sessions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Check if messages table exists and has the correct schema
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
    messages_exists = c.fetchone()
    
    needs_migration = False
    if messages_exists:
        # Check columns
        c.execute("PRAGMA table_info(messages)")
        columns = [info[1] for info in c.fetchall()]
        if "session_id" not in columns or "metadata" not in columns:
            needs_migration = True
    
    if needs_migration:
        print("Migrating database schema...")
        # Rename old table
        c.execute("ALTER TABLE messages RENAME TO messages_old")
        
        # Create new table
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            )
        ''')
        
        # Create a legacy session for old messages
        c.execute("INSERT INTO sessions (title) VALUES (?)", ("Legacy Session",))
        legacy_session_id = c.lastrowid
        
        # Migrate old messages
        c.execute("SELECT role, content, timestamp FROM messages_old")
        old_messages = c.fetchall()
        
        for role, content, timestamp in old_messages:
            c.execute('''
                INSERT INTO messages (session_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (legacy_session_id, role, content, timestamp))
            
        # Optional: Drop old table or keep for backup. Keeping for safety.
        # c.execute("DROP TABLE messages_old") 
        print(f"Migration complete. {len(old_messages)} messages moved to Legacy Session.")
        
    else:
        # Create table if it doesn't exist at all
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            )
        ''')
        
    conn.commit()
    conn.close()

def create_session(title: str = "New Chat"):
    """Create a new chat session."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO sessions (title) VALUES (?)", (title,))
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    return session_id

def get_sessions():
    """Get all sessions ordered by creation time (newest first)."""
    if not os.path.exists(DB_FILE):
        return []
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, title, created_at FROM sessions ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    
    return [{"id": row[0], "title": row[1], "created_at": row[2]} for row in rows]

def delete_session(session_id: int):
    """Delete a session and all its messages."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

def save_message(session_id: int, role: str, content: str, metadata: dict = None):
    """Save a new message to the database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    metadata_json = json.dumps(metadata) if metadata else None
    
    c.execute('''
        INSERT INTO messages (session_id, role, content, metadata) 
        VALUES (?, ?, ?, ?)
    ''', (session_id, role, content, metadata_json))
    
    conn.commit()
    conn.close()

def load_history(session_id: int):
    """Load messages for a specific session."""
    if not os.path.exists(DB_FILE):
        return []
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT role, content, metadata 
        FROM messages 
        WHERE session_id = ? 
        ORDER BY timestamp ASC
    ''', (session_id,))
    rows = c.fetchall()
    conn.close()
    
    messages = []
    for row in rows:
        msg = {
            "role": row[0], 
            "content": row[1]
        }
        if row[2]:
            try:
                msg["metadata"] = json.loads(row[2])
            except:
                msg["metadata"] = None
        else:
            msg["metadata"] = None
        messages.append(msg)
        
    return messages

if __name__ == "__main__":
    init_db()
