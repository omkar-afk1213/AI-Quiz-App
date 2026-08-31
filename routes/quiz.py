import html
import json
import re
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from models.db import get_db
from models.quiz import QuizAttempt
from services.performance_analyzer import PerformanceAnalyzer
from services.quiz_generator import QuizGenerator

quiz_bp = Blueprint("quiz", __name__)


@quiz_bp.route("/home")
@login_required
def home():
    return render_template("quiz/home.html", username=current_user.username)


@quiz_bp.route("/setup", methods=["GET", "POST"])
@login_required
def setup():
    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        count = request.form.get("count", "5")
        difficulty = request.form.get("difficulty", "medium")
        topic = re.sub(r"<.*?>", "", topic)
        topic = topic[:100]

        if not topic:
            flash("Please enter a quiz topic.", "danger")
            return render_template("quiz/setup.html")

        difficulty = str(difficulty or "medium").strip().lower()
        if difficulty not in {"easy", "medium", "hard"}:
            difficulty = "medium"

        try:
            count = int(count)
        except ValueError:
            count = 5
        if count not in {5, 10, 15, 20}:
            count = 5

        if "quiz_generation_count" not in session:
            session["quiz_generation_count"] = 0
            session["quiz_generation_window"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        session["topic"] = topic
        session["question_count"] = count
        session["difficulty"] = difficulty
        session["quiz_questions"] = []

        try:
            generated = QuizGenerator.generate(topic, count, difficulty=difficulty)
            session["quiz_questions"] = generated
            session["quiz_generation_count"] = int(session.get("quiz_generation_count", 0)) + 1
            return redirect(url_for("quiz.take"))
        except Exception as exc:
            flash(str(exc), "danger")
            return render_template("quiz/setup.html")

    return render_template("quiz/setup.html")


@quiz_bp.route("/take")
@login_required
def take():
    questions = session.get("quiz_questions", [])
    if not questions:
        flash("Please generate a quiz first.", "warning")
        return redirect(url_for("quiz.setup"))

    q_index = int(request.args.get("q", 0))
    if q_index >= len(questions):
        q_index = len(questions) - 1
    question = questions[q_index]
    return render_template("quiz/take.html", questions=questions, question=question, q_index=q_index, total=len(questions))


@quiz_bp.route("/submit", methods=["POST"])
@login_required
def submit():
    questions = session.get("quiz_questions", [])
    if not questions:
        flash("No quiz found in session.", "warning")
        return redirect(url_for("quiz.setup"))

    user_answers = []
    score = 0
    answers_for_db = []
    topic = session.get("topic", "General")
    difficulty = session.get("difficulty", "medium")

    for index, question in enumerate(questions):
        answer_key = f"question_{index}"
        selected = request.form.get(answer_key, "")
        is_correct = selected == question["answer"]
        if is_correct:
            score += 1
        user_answers.append({
            "question": question["question"],
            "options": question["options"],
            "answer": question["answer"],
            "user_answer": selected,
            "is_correct": is_correct,
        })
        answers_for_db.append({
            "question": question["question"],
            "options": question["options"],
            "answer": question["answer"],
            "user_answer": selected,
        })

    total = len(questions)
    ai_model = "gemini"
    db = get_db()
    row = db.execute("SELECT active_model FROM ai_settings ORDER BY id DESC LIMIT 1").fetchone()
    if row:
        ai_model = row["active_model"]

    attempt_id = QuizAttempt.save_attempt(current_user.id, topic, total, score, total, ai_model, answers_for_db)

    session["last_result"] = {
        "score": score,
        "total": total,
        "topic": topic,
        "difficulty": difficulty,
        "answers": user_answers,
        "attempt_id": attempt_id,
    }
    session.pop("quiz_questions", None)
    session.pop("topic", None)
    session.pop("question_count", None)
    session.pop("difficulty", None)
    return redirect(url_for("quiz.result"))


@quiz_bp.route("/result")
@login_required
def result():
    result_data = session.get("last_result")
    if not result_data:
        flash("You do not have a recent quiz result to view.", "warning")
        return redirect(url_for("quiz.home"))

    analysis = PerformanceAnalyzer.analyze(current_user.id)
    return render_template("quiz/result.html", result=result_data, analysis=analysis)


@quiz_bp.route("/history")
@login_required
def history():
    attempts = QuizAttempt.get_attempts_by_user(current_user.id)
    for attempt in attempts:
        attempt["percentage"] = round((attempt["score"] / attempt["total"]) * 100, 2) if attempt["total"] else 0
    return render_template("quiz/history.html", attempts=attempts)
