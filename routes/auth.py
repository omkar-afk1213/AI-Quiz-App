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
