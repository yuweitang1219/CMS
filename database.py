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
            completed_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        cursor.execute("ALTER TABLE todos ADD COLUMN completed_at TEXT")
    except sqlite3.OperationalError:
        pass
    
    # Create settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # Create cases table to track last visit dates and addresses for re-evaluation reminders & route planning
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            name TEXT PRIMARY KEY,
            address TEXT,
            last_visit_date TEXT,
            plan_type TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    rows = cursor.execute("""
        SELECT * FROM todos 
        WHERE completed = 0 
           OR (completed = 1 AND completed_at >= datetime('now', '-1 day'))
        ORDER BY completed ASC, created_at DESC
    """).fetchall()
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
        if int(completed) == 1:
            updates.append("completed_at = datetime('now')")
        else:
            updates.append("completed_at = NULL")
        
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

# --- Cases Functions ---
def update_case_record(name, last_visit_date=None, address=None, plan_type=None):
    if not name or name == "未提供資料":
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM cases WHERE name = ?", (name,)).fetchone()
    if row:
        curr_address = address if (address is not None and address != "") else row["address"]
        curr_visit = last_visit_date if (last_visit_date is not None and last_visit_date != "") else row["last_visit_date"]
        curr_plan = plan_type if (plan_type is not None and plan_type != "") else row["plan_type"]
        cursor.execute(
            "UPDATE cases SET address = ?, last_visit_date = ?, plan_type = ?, updated_at = CURRENT_TIMESTAMP WHERE name = ?",
            (curr_address, curr_visit, curr_plan, name)
        )
    else:
        cursor.execute(
            "INSERT INTO cases (name, address, last_visit_date, plan_type) VALUES (?, ?, ?, ?)",
            (name, address, last_visit_date, plan_type)
        )
    conn.commit()
    conn.close()

def format_roc_month(date_str):
    """
    Formats ISO date string 'YYYY-MM-DD' or 'YYYY-MM' into ROC Year & Month '115年7月' without days.
    """
    if not date_str:
        return ""
    try:
        parts = date_str.split("-")
        roc_year = int(parts[0]) - 1911
        month = int(parts[1])
        return f"{roc_year}年{month}月"
    except Exception:
        return date_str

def calculate_next_visit_due_date(vdate, plan_type=None):
    """
    Calculates the next visit / re-evaluation due date based on plan type:
    - ReEval (複評): 1 year (12 months)
    - AA01 / NewCase (新案) / others: 6 months (月份 + 6)
    """
    import datetime
    import calendar
    
    pt = str(plan_type).lower() if plan_type else ""
    if pt in ["reeval", "複評"]:
        months_to_add = 12
    else:
        months_to_add = 6
        
    year = vdate.year
    month = vdate.month + months_to_add
    while month > 12:
        year += 1
        month -= 12
    max_days = calendar.monthrange(year, month)[1]
    day = min(vdate.day, max_days)
    return datetime.date(year, month, day)

def get_due_reevaluations(window_days=30):
    """
    Returns cases whose next visit / re-evaluation is approaching or past.
    """
    import datetime
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM cases WHERE last_visit_date IS NOT NULL AND last_visit_date != ''").fetchall()
    conn.close()
    
    due_cases = []
    today = datetime.date.today()
    for row in rows:
        vdate_str = row["last_visit_date"]
        try:
            vdate = datetime.date.fromisoformat(vdate_str)
        except Exception:
            continue
            
        due_date = calculate_next_visit_due_date(vdate, row["plan_type"])
        next_due_days = (due_date - today).days
        
        if next_due_days <= window_days:
            due_cases.append({
                "name": row["name"],
                "last_visit_date": vdate_str,
                "due_date": due_date.isoformat(),
                "next_due_days": next_due_days,
                "is_overdue": next_due_days < 0,
                "plan_type": row["plan_type"]
            })
            
    due_cases.sort(key=lambda x: x["next_due_days"])
    return due_cases

def is_first_working_day_of_month(d=None):
    """
    Determines if `d` (datetime.date) is the first Monday-Friday of its month.
    """
    import datetime
    if not d:
        local_now = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        d = local_now.date()
    first_day = datetime.date(d.year, d.month, 1)
    while first_day.weekday() >= 5: # 5=Saturday, 6=Sunday
        first_day += datetime.timedelta(days=1)
    return d == first_day

def get_current_month_due_cases(year=None, month=None):
    """
    Returns all cases whose next visit / re-evaluation falls in the target year & month.
    """
    import datetime
    if not year or not month:
        local_now = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        year, month = local_now.year, local_now.month
        
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM cases WHERE last_visit_date IS NOT NULL AND last_visit_date != ''").fetchall()
    conn.close()
    
    due_cases = []
    for row in rows:
        vdate_str = row["last_visit_date"]
        try:
            vdate = datetime.date.fromisoformat(vdate_str)
        except Exception:
            continue
            
        due_date = calculate_next_visit_due_date(vdate, row["plan_type"])
        if due_date.year == year and due_date.month == month:
            due_cases.append({
                "name": row["name"],
                "last_visit_date": vdate_str,
                "due_date": due_date.isoformat(),
                "address": row["address"],
                "plan_type": row["plan_type"]
            })
            
    due_cases.sort(key=lambda x: x["due_date"])
    return due_cases

def get_case_by_name(name):
    conn = get_db_connection()
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM cases WHERE name = ?", (name,)).fetchone()
    conn.close()
    return dict(row) if row else None

# Initialize DB on import
init_db()
