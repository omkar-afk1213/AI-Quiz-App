import os
import re
import unittest
from uuid import uuid4

from app import app
from models.db import get_db
from models.user import User


class EndToEndTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_gemini = os.environ.pop("GEMINI_API_KEY", None)
        cls.old_openai = os.environ.pop("OPENAI_API_KEY", None)
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    @classmethod
    def tearDownClass(cls):
        if cls.old_gemini is not None:
            os.environ["GEMINI_API_KEY"] = cls.old_gemini
        if cls.old_openai is not None:
            os.environ["OPENAI_API_KEY"] = cls.old_openai

    def setUp(self):
        self.client = app.test_client()
        self.username = f"e2e_{uuid4().hex[:8]}"
        with app.app_context():
            User.create_user(self.username, "oldpass123", email=f"{self.username}@example.com")

    def tearDown(self):
        with app.app_context():
            db = get_db()
            user = User.get_by_username(self.username)
            if user:
                db.execute("DELETE FROM quiz_attempts WHERE user_id = ?", (user.id,))
                db.execute("DELETE FROM reset_tokens WHERE user_id = ?", (user.id,))
                db.execute("DELETE FROM users WHERE id = ?", (user.id,))
                db.commit()

    def login(self, username, password, role):
        return self.client.post("/login", data={"username": username, "password": password, "role": role}, follow_redirects=False)

    def test_admin_user_quiz_history_and_password_reset_flow(self):
        admin_response = self.login("admin", "admin123", "admin")
        self.assertEqual(admin_response.status_code, 302)
        self.assertIn("/admin/dashboard", admin_response.headers["Location"])

        attempts_response = self.client.get("/admin/attempts")
        self.assertEqual(attempts_response.status_code, 200)
        self.assertIn(b"All Quiz Attempts", attempts_response.data)

        self.client.get("/logout")
        user_response = self.login(self.username, "oldpass123", "user")
        self.assertEqual(user_response.status_code, 302)
        self.assertIn("/quiz/home", user_response.headers["Location"])

        setup_response = self.client.post(
            "/quiz/setup",
            data={"topic": "Python Basics", "count": "5", "difficulty": "hard"},
            follow_redirects=False,
        )
        self.assertEqual(setup_response.status_code, 302)
        self.assertIn("/quiz/take", setup_response.headers["Location"])

        with self.client.session_transaction() as session:
            questions = session["quiz_questions"]
            self.assertEqual(session["difficulty"], "hard")

        answers = {f"question_{index}": question["answer"] for index, question in enumerate(questions)}
        result_response = self.client.post("/quiz/submit", data=answers, follow_redirects=False)
        self.assertEqual(result_response.status_code, 302)
        self.assertIn("/quiz/result", result_response.headers["Location"])

        with app.app_context():
            user = User.get_by_username(self.username)
            attempt = get_db().execute(
                "SELECT difficulty FROM quiz_attempts WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                (user.id,),
            ).fetchone()
            self.assertEqual(attempt["difficulty"], "hard")

        history_response = self.client.get("/quiz/history")
        self.assertEqual(history_response.status_code, 200)
        self.assertIn(b"Difficulty", history_response.data)

        self.client.get("/logout")
        forgot_response = self.client.post("/forgot-password", data={"username": self.username})
        self.assertEqual(forgot_response.status_code, 200)
        self.assertIn(b"Reset link", forgot_response.data)
        reset_match = re.search(rb'href="([^"]+/reset-password/([^"]+))"', forgot_response.data)
        self.assertIsNotNone(reset_match)
        reset_url = reset_match.group(1).decode("utf-8")
        reset_response = self.client.post(
            reset_url,
            data={"password": "newpass123", "confirm_password": "newpass123"},
            follow_redirects=False,
        )
        self.assertEqual(reset_response.status_code, 302)
        self.assertIn("/login", reset_response.headers["Location"])
        new_login = self.login(self.username, "newpass123", "user")
        self.assertEqual(new_login.status_code, 302)
        self.assertIn("/quiz/home", new_login.headers["Location"])

        with app.app_context():
            token_hash = get_db().execute(
                "SELECT token_hash FROM reset_tokens WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                (User.get_by_username(self.username).id,),
            ).fetchone()["token_hash"]
            self.assertTrue(token_hash)


if __name__ == "__main__":
    unittest.main()
