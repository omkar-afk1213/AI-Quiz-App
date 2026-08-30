from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from models.db import get_db
from models.quiz import QuizAttempt
from models.user import User

admin_bp = Blueprint("admin", __name__)


def admin_required(function):
    from functools import wraps

    @wraps(function)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role != "admin":
            return render_template("403.html"), 403
        return function(*args, **kwargs)

    return wrapper


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    total_users = User.count_users()
    total_quizzes = QuizAttempt.get_total_attempts()
    average_score = QuizAttempt.get_average_score()
    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_quizzes=total_quizzes,
        average_score=round(average_score, 2),
    )


@admin_bp.route("/users", methods=["GET", "POST"])
@admin_required
def users():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            if username and password:
                if not User.get_by_username(username):
                    User.create_user(username, password, email=email, role="user")
                    flash("User created successfully.", "success")
                else:
                    flash("Username already exists.", "danger")
        elif action == "delete":
            user_id = request.form.get("user_id")
            if user_id and int(user_id) != current_user.id:
                User.delete_user(int(user_id))
                flash("User deleted.", "success")

    users_list = User.get_all()
    return render_template("admin/users.html", users=users_list)


@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    db = get_db()
    if request.method == "POST":
        active_model = request.form.get("active_model", "gemini").strip().lower()
        gemini_key = request.form.get("gemini_key", "").strip()
        openai_key = request.form.get("openai_key", "").strip()

        if active_model not in {"gemini", "openai"}:
            active_model = "gemini"
        if gemini_key:
            db.execute("UPDATE ai_settings SET active_model = ?, updated_at = datetime('now')", (active_model,))
            import os
            os.environ["GEMINI_API_KEY"] = gemini_key
        if openai_key:
            db.execute("UPDATE ai_settings SET active_model = ?, updated_at = datetime('now')", (active_model,))
            import os
            os.environ["OPENAI_API_KEY"] = openai_key
        db.execute("UPDATE ai_settings SET active_model = ?, updated_at = datetime('now')", (active_model,))
        db.commit()
        flash("AI settings saved.", "success")

    row = db.execute("SELECT * FROM ai_settings ORDER BY id DESC LIMIT 1").fetchone()
    return render_template("admin/settings.html", active_model=row["active_model"] if row else "gemini")
