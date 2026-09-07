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
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        page = 1
    per_page = 10
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

    users_list = User.get_all(page, per_page)
    total_users = User.count_all()
    total_pages = max((total_users + per_page - 1) // per_page, 1)
    return render_template("admin/users.html", users=users_list, page=page, total_pages=total_pages)


@admin_bp.route("/attempts")
@admin_required
def attempts():
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        page = 1
    per_page = 10
    attempts_list = QuizAttempt.get_all_attempts(page, per_page)
    for attempt in attempts_list:
        attempt["percentage"] = round((attempt["score"] / attempt["total"]) * 100, 2) if attempt["total"] else 0
    total_attempts = QuizAttempt.count_all_attempts()
    total_pages = max((total_attempts + per_page - 1) // per_page, 1)
    return render_template("admin/attempts.html", attempts=attempts_list, page=page, total_pages=total_pages)


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
        from services.ai_service import AIService
        if gemini_key:
            AIService.save_api_key("gemini", gemini_key)
        if openai_key:
            AIService.save_api_key("openai", openai_key)
        db.execute("UPDATE ai_settings SET active_model = ?, updated_at = datetime('now')", (active_model,))
        db.commit()
        flash("AI settings saved.", "success")

    row = db.execute("SELECT * FROM ai_settings ORDER BY id DESC LIMIT 1").fetchone()
    return render_template("admin/settings.html", active_model=row["active_model"] if row else "gemini")
