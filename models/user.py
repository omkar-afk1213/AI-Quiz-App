import sqlite3

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from models.db import DB_PATH, get_db


class User(UserMixin):
    def __init__(self, id, username, email=None, password_hash="", role="user", created_at=None, is_active=1):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.created_at = created_at
        self.active = bool(is_active)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_active(self):
        return self.active

    @staticmethod
    def create_user(username, password, email=None, role="user"):
        db = get_db()
        password_hash = generate_password_hash(password)
        cursor = db.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (username, email, password_hash, role),
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def create_admin(username, password):
        return User.create_user(username, password, role="admin")

    @staticmethod
    def get_by_username(username):
        db = get_db()
        row = db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if not row:
            return None
        return User(**dict(row))

    @staticmethod
    def get_by_id(user_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return User(**dict(row))

    @staticmethod
    def get_all():
        db = get_db()
        rows = db.execute("SELECT * FROM users ORDER BY id ASC").fetchall()
        return [User(**dict(row)) for row in rows]

    @staticmethod
    def verify_login(username, password):
        user = User.get_by_username(username)
        if user and check_password_hash(user.password_hash, password):
            return user
        return None

    @staticmethod
    def delete_user(user_id):
        db = get_db()
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()

    @staticmethod
    def count_users():
        db = get_db()
        row = db.execute("SELECT COUNT(*) as count FROM users").fetchone()
        return row["count"] if row else 0

    @staticmethod
    def get_stats():
        db = get_db()
        row = db.execute(
            "SELECT COUNT(*) as total_users FROM users"
        ).fetchone()
        return {"total_users": row["total_users"] if row else 0}
