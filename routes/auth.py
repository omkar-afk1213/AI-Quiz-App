from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user
from werkzeug.security import generate_password_hash

from config import Config
from models.db import get_db
from models.user import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    login_role = request.form.get("role", "admin") if request.method == "POST" else "admin"

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember_me"))

        user = User.verify_login(username, password)
        if user and ((login_role == "admin" and user.role == "admin") or (login_role == "user" and user.role == "user")):
            login_user(user, remember=remember)
            if user.role == "admin":
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("quiz.home"))

        if username and password:
            flash("Invalid username or password for the selected login type.", "danger")
        else:
            flash("Username and password are required.", "danger")
        return render_template("auth/login.html", login_role=login_role)

    return render_template("auth/login.html", login_role=login_role)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("auth/register.html")
        if len(username) > 50:
            flash("Username is too long.", "danger")
            return render_template("auth/register.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")
        if User.get_by_username(username):
            flash("Username already exists.", "danger")
            return render_template("auth/register.html")

        User.create_user(username, password, email=email, role="user")
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    reset_url = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        token = User.create_password_reset(username)
        flash("If that account exists, a password reset link has been created.", "info")
        if token:
            reset_url = url_for("auth.reset_password", token=token, _external=True)
    return render_template("auth/forgot_password.html", reset_url=reset_url)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.get_by_reset_token(token)
    if not user:
        flash("This reset link is invalid or expired.", "danger")
        return redirect(url_for("auth.forgot_password"))
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        else:
            User.consume_reset_token(token, user.id, password)
            flash("Password reset successfully. Please log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html")
