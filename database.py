import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_data.db")


def _execute(sql, params=(), fetch=False):
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(sql, params)
        rows = cur.fetchall() if fetch else None
        conn.commit()
        return rows if fetch else cur.lastrowid
    finally:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS captures (
            capture_id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL, capture_type TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            width INTEGER, height INTEGER);
        CREATE TABLE IF NOT EXISTS ai_prompt_log (
            prompt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            capture_id INTEGER REFERENCES captures(capture_id),
            prompt_text TEXT, response_json TEXT, status TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS templates (
            template_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, kind TEXT NOT NULL, content TEXT NOT NULL);
        """)
        conn.commit()
    finally:
        conn.close()


def get_setting(key, default=""):
    rows = _execute("SELECT value FROM settings WHERE key=?", (key,), fetch=True)
    return rows[0][0] if rows else default


def set_setting(key, value):
    _execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)", (key, value))


def log_capture(file_path, capture_type, width, height):
    return _execute(
        "INSERT INTO captures(file_path, capture_type, width, height) VALUES(?, ?, ?, ?)",
        (file_path, capture_type, width, height))


def log_prompt(capture_id, prompt_text, response_json, status):
    _execute(
        "INSERT INTO ai_prompt_log(capture_id, prompt_text, response_json, status) VALUES(?, ?, ?, ?)",
        (capture_id, prompt_text, response_json, status))


def add_template(name, kind, content):
    return _execute("INSERT INTO templates(name, kind, content) VALUES(?, ?, ?)",
                    (name, kind, content))


def list_templates(kind):
    return _execute("SELECT template_id, name, content FROM templates WHERE kind=?",
                    (kind,), fetch=True)