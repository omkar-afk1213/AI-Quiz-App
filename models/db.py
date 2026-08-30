import sqlite3
from pathlib import Path

from flask import current_app, g

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "quiz.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
        db.executescript(file.read())

    from models.user import User

    if not User.get_by_username("admin"):
        User.create_admin("admin", "Admin@123")

    settings = db.execute("SELECT * FROM ai_settings").fetchone()
    if settings is None:
        db.execute(
            "INSERT INTO ai_settings (active_model, updated_at) VALUES (?, datetime('now'))",
            ("gemini",),
        )

    db.commit()
    db.close()


def query_db(query, params=(), one=False):
    db = get_db()
    cursor = db.execute(query, params)
    rows = cursor.fetchall()
    db.commit()
    return (rows[0] if rows else None) if one else rows
