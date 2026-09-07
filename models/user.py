import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

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
    def get_all(page=1, per_page=10):
        db = get_db()
        offset = (page - 1) * per_page
        rows = db.execute("SELECT * FROM users ORDER BY id ASC LIMIT ? OFFSET ?", (per_page, offset)).fetchall()
        return [User(**dict(row)) for row in rows]

    @staticmethod
    def count_all():
        db = get_db()
        row = db.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        return row["count"] if row else 0

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
    def create_password_reset(username):
        user = User.get_by_username(username)
        if not user:
            return None
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
        db = get_db()
        db.execute("UPDATE reset_tokens SET used_at = datetime('now') WHERE user_id = ? AND used_at IS NULL", (user.id,))
        db.execute(
            "INSERT INTO reset_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (user.id, token_hash, expires_at),
        )
        db.commit()
        return token

    @staticmethod
    def get_by_reset_token(token):
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        db = get_db()
        row = db.execute(
            "SELECT users.* FROM reset_tokens JOIN users ON users.id = reset_tokens.user_id "
            "WHERE reset_tokens.token_hash = ? AND reset_tokens.used_at IS NULL AND reset_tokens.expires_at > ?",
            (token_hash, datetime.now(timezone.utc).isoformat()),
        ).fetchone()
        return User(**dict(row)) if row else None

    @staticmethod
    def consume_reset_token(token, user_id, new_password):
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        db = get_db()
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new_password), user_id))
        db.execute(
            "UPDATE reset_tokens SET used_at = datetime('now') WHERE token_hash = ? AND user_id = ?",
            (token_hash, user_id),
        )
        db.commit()

    @staticmethod
    def get_stats():
        db = get_db()
        row = db.execute(
            "SELECT COUNT(*) as total_users FROM users"
        ).fetchone()
        return {"total_users": row["total_users"] if row else 0}
