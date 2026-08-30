from flask import Flask, redirect, render_template, url_for
from flask_login import LoginManager, current_user

from config import Config
from models.db import init_db
from models.user import User
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.quiz import quiz_bp

app = Flask(__name__)
app.config.from_object(Config)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)


@app.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("quiz.home"))
    return redirect(url_for("auth.login"))


@app.errorhandler(403)
def forbidden_error(error):
    return render_template("403.html"), 403


app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(quiz_bp, url_prefix="/quiz")

with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
