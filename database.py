import sqlite3
import os

# Detect if running in a cloud hosting container (like Render) with a persistent volume mounted at /data
if os.path.exists("/data") and os.path.isdir("/data"):
    DB_PATH = "/data/dashboard.db"
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create todos table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'medium', -- low, medium, high
            due_date TEXT,
            completed INTEGER DEFAULT 0, -- 0 for False, 1 for True
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    conn.commit()
    conn.close()

# --- User Functions ---
def create_user(username, password_hash):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None

def has_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    row = cursor.execute("SELECT COUNT(*) as count FROM users").fetchone()
    conn.close()
    return row["count"] > 0

# --- Todo Functions ---
def get_todos():
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM todos ORDER BY completed ASC, created_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_todo(title, priority='medium', due_date=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO todos (title, priority, due_date) VALUES (?, ?, ?)",
        (title, priority, due_date)
    )
    todo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return todo_id

def update_todo(todo_id, title=None, priority=None, due_date=None, completed=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if priority is not None:
        updates.append("priority = ?")
        params.append(priority)
    if due_date is not None:
        updates.append("due_date = ?")
        params.append(due_date)
    if completed is not None:
        updates.append("completed = ?")
        params.append(int(completed))
        
    if not updates:
        conn.close()
        return False
        
    params.append(todo_id)
    query = f"UPDATE todos SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, tuple(params))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def delete_todo(todo_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

# --- Settings Functions ---
def get_setting(key, default=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    row = cursor.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, str(value) if value is not None else None)
    )
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()
