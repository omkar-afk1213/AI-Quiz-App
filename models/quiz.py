import json
import sqlite3
from datetime import datetime

from models.db import get_db


class QuizAttempt:
    @staticmethod
    def save_attempt(user_id, topic, num_questions, score, total, ai_model_used, answers):
        db = get_db()
        attempt_cursor = db.execute(
            "INSERT INTO quiz_attempts (user_id, topic, num_questions, score, total, ai_model_used, taken_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
            (user_id, topic, num_questions, score, total, ai_model_used),
        )
        attempt_id = attempt_cursor.lastrowid
        for item in answers:
            db.execute(
                "INSERT INTO attempt_answers (attempt_id, question_text, options_json, correct_answer, user_answer, is_correct) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    attempt_id,
                    item["question"],
                    json.dumps(item["options"]),
                    item["answer"],
                    item.get("user_answer"),
                    1 if item.get("user_answer") == item["answer"] else 0,
                ),
            )
        db.commit()
        return attempt_id

    @staticmethod
    def get_attempts_by_user(user_id):
        db = get_db()
        rows = db.execute(
            "SELECT * FROM quiz_attempts WHERE user_id = ? ORDER BY taken_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get_attempt_details(attempt_id):
        db = get_db()
        rows = db.execute(
            "SELECT * FROM attempt_answers WHERE attempt_id = ? ORDER BY id ASC",
            (attempt_id,),
        ).fetchall()
        result = []
        for row in rows:
            result.append({
                "question": row["question_text"],
                "options": json.loads(row["options_json"]),
                "correct_answer": row["correct_answer"],
                "user_answer": row["user_answer"],
                "is_correct": bool(row["is_correct"]),
            })
        return result

    @staticmethod
    def get_all_attempts():
        db = get_db()
        rows = db.execute(
            "SELECT * FROM quiz_attempts ORDER BY taken_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get_average_score():
        db = get_db()
        row = db.execute("SELECT AVG(score * 100.0 / total) AS avg FROM quiz_attempts").fetchone()
        return float(row["avg"]) if row and row["avg"] is not None else 0.0

    @staticmethod
    def get_total_attempts():
        db = get_db()
        row = db.execute("SELECT COUNT(*) AS count FROM quiz_attempts").fetchone()
        return row["count"] if row else 0

    @staticmethod
    def get_user_result_score(user_id):
        attempts = QuizAttempt.get_attempts_by_user(user_id)
        if not attempts:
            return 0
        return sum(attempt["score"] for attempt in attempts)


class Answer:
    @staticmethod
    def get_by_attempt(attempt_id):
        return QuizAttempt.get_attempt_details(attempt_id)
