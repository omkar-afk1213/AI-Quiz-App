import base64
import hashlib
import json
import os

from flask import current_app
from cryptography.fernet import Fernet

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover
    genai = None

from openai import OpenAI


class AIService:
    def __init__(self):
        self.available_models = ["gemini", "openai"]

    def _clean_topic(self, topic: str) -> str:
        cleaned = topic.strip()
        if len(cleaned) > 100:
            cleaned = cleaned[:100]
        return cleaned

    def _get_model_settings(self):
        try:
            from flask import has_app_context
            if not has_app_context():
                return "gemini"
            db = __import__("models.db", fromlist=["get_db"]).get_db()
            row = db.execute("SELECT active_model FROM ai_settings ORDER BY id DESC LIMIT 1").fetchone()
            return (row["active_model"] if row else "gemini").strip().lower()
        except Exception:
            return "gemini"

    @staticmethod
    def _fernet():
        secret = current_app.config["SECRET_KEY"].encode("utf-8")
        key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
        return Fernet(key)

    @classmethod
    def save_api_key(cls, provider, api_key):
        if provider not in {"gemini", "openai"}:
            raise ValueError("Unsupported AI provider")
        db = __import__("models.db", fromlist=["get_db"]).get_db()
        encrypted_key = cls._fernet().encrypt(api_key.encode("utf-8")).decode("utf-8")
        db.execute(
            "INSERT INTO ai_credentials (provider, encrypted_key, updated_at) VALUES (?, ?, datetime('now')) "
            "ON CONFLICT(provider) DO UPDATE SET encrypted_key = excluded.encrypted_key, updated_at = excluded.updated_at",
            (provider, encrypted_key),
        )
        db.commit()

    @classmethod
    def _get_api_key(cls, provider):
        try:
            db = __import__("models.db", fromlist=["get_db"]).get_db()
            row = db.execute("SELECT encrypted_key FROM ai_credentials WHERE provider = ?", (provider,)).fetchone()
            if row:
                return cls._fernet().decrypt(row["encrypted_key"].encode("utf-8")).decode("utf-8")
        except Exception:
            pass
        return os.getenv("GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY")

    @staticmethod
    def _safe_json_extract(text):
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            if stripped.lower().startswith("json"):
                stripped = stripped[4:].strip()
        return json.loads(stripped)

    def generate_questions(self, topic: str, count: int, difficulty: str = "medium") -> list[dict]:
        safe_topic = self._clean_topic(topic)
        normalized = str(difficulty or "medium").strip().lower()
        if normalized not in {"easy", "medium", "hard"}:
            normalized = "medium"

        prompt = (
            f"Generate {count} multiple choice questions about '{safe_topic}' at {normalized} difficulty. "
            "Return ONLY a valid JSON array. Each item must have exactly these fields: "
            '"question": the question text, "options": array of exactly 4 answer choices, "answer": the exact text of the correct option, "explanation": one sentence explaining why it is correct. " '
            "Ensure the wording and complexity match the selected difficulty level. "
            "Return nothing else, just the JSON array."
        )

        primary_model = self._get_model_settings()
        models = [primary_model] if primary_model in self.available_models else ["gemini", "openai"]
        if primary_model == "gemini":
            models = ["gemini", "openai"]
        elif primary_model == "openai":
            models = ["openai", "gemini"]

        last_error = None
        for model_name in models:
            try:
                if model_name == "gemini":
                    questions = self._generate_with_gemini(prompt)
                else:
                    questions = self._generate_with_openai(prompt)
                if isinstance(questions, list) and questions:
                    return questions
                raise ValueError("Empty or invalid response from AI model")
            except Exception as exc:  # pragma: no cover
                last_error = exc
                continue

        return self._generate_fallback_questions(safe_topic, count, normalized)

    def _generate_fallback_questions(self, topic: str, count: int, difficulty: str = "medium") -> list[dict]:
        base_topic = topic or "General Knowledge"
        profiles = {
            "easy": [
                (f"What is {base_topic} mainly about?", "It introduces the basic ideas of the topic", "Easy questions check core definitions and recognition."),
                (f"Which is a good first step when learning {base_topic}?", "Learn the basic terms and examples", "Beginners benefit from learning foundational terms first."),
                (f"What helps a learner remember {base_topic}?", "Simple practice and review", "Short practice sessions help reinforce new concepts."),
                (f"Which statement is true about {base_topic}?", "It becomes easier with clear examples", "Examples connect a new topic to familiar situations."),
                (f"What should you do when a {base_topic} idea is unclear?", "Review the explanation and ask for help", "Reviewing and asking questions builds understanding."),
            ],
            "medium": [
                (f"Which approach best improves performance in {base_topic}?", "Regular practice and review", "Consistent review and practice strengthen learning and retention."),
                (f"Why should explanations be reviewed in {base_topic}?", "They clarify why an answer is correct", "Explanations help learners understand the reasoning behind answers."),
                (f"Which statement is most accurate about applying {base_topic}?", "It requires understanding, application, and practice", "Strong performance combines knowledge with practical use."),
                (f"How can a learner improve after a mistake in {base_topic}?", "Review the mistake and correct the reasoning", "Analyzing mistakes turns errors into learning opportunities."),
                (f"Which behavior supports progress in {base_topic}?", "Using feedback to adjust future practice", "Feedback helps learners focus their next practice session."),
            ],
            "hard": [
                (f"A learner can explain {base_topic} but cannot apply it. What is the best diagnosis?", "They need deliberate practice in realistic situations", "Application gaps are addressed through targeted, realistic practice."),
                (f"Which strategy best tests mastery of {base_topic}?", "Compare multiple solutions and justify the trade-offs", "Mastery includes evaluating alternatives and defending a choice."),
                (f"When a result in {base_topic} conflicts with expectations, what should happen first?", "Check assumptions, evidence, and the reasoning chain", "Unexpected results require systematic verification before conclusions."),
                (f"Which learner is most likely to retain {base_topic} long term?", "One who retrieves ideas, applies them, and reviews mistakes", "Retrieval, application, and reflection reinforce durable learning."),
                (f"What is the strongest evidence that someone understands {base_topic}?", "They can adapt the concept to a new problem", "Transfer to unfamiliar problems is a stronger signal than recall alone."),
            ],
        }
        templates = profiles.get(difficulty, profiles["medium"])
        questions = []
        wrong_options = [
            "Avoid the topic entirely",
            "Guess without checking the reasoning",
            "Memorize one answer and skip practice",
        ]

        for i in range(count):
            question_text, answer, explanation = templates[i % len(templates)]
            options = [answer] + wrong_options
            question = {
                "question": question_text,
                "options": options,
                "answer": answer,
                "explanation": explanation,
            }
            questions.append(question)

        return questions[:count]

    def _generate_with_gemini(self, prompt):
        api_key = self._get_api_key("gemini")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing")
        if genai is None:
            raise ValueError("google-generativeai is not installed")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        text = getattr(response, "text", "")
        if not text:
            raise ValueError("Empty Gemini response")
        return self._safe_json_extract(text)

    def _generate_with_openai(self, prompt):
        api_key = self._get_api_key("openai")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing")
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500,
            temperature=0.6,
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty OpenAI response")
        return self._safe_json_extract(content)
