import json
import os

from flask import current_app

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
    def _safe_json_extract(text):
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            if stripped.lower().startswith("json"):
                stripped = stripped[4:].strip()
        return json.loads(stripped)

    def generate_questions(self, topic: str, count: int) -> list[dict]:
        safe_topic = self._clean_topic(topic)
        prompt = (
            f"Generate {count} multiple choice questions about '{safe_topic}'. "
            "Return ONLY a valid JSON array. Each item must have exactly these fields: "
            '"question": the question text, "options": array of exactly 4 answer choices, "answer": the exact text of the correct option, "explanation": one sentence explaining why it is correct. " '
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

        return self._generate_fallback_questions(safe_topic, count)

    def _generate_fallback_questions(self, topic: str, count: int) -> list[dict]:
        base_topic = topic or "General Knowledge"
        questions = []
        templates = [
            {
                "question": f"What is the main goal of learning {base_topic}?",
                "options": [
                    "To understand key concepts and improve skills",
                    "To avoid studying entirely",
                    "To skip practice and memorize nothing",
                    "To ignore real-world examples"
                ],
                "answer": "To understand key concepts and improve skills",
                "explanation": "Studying a topic helps build understanding and practical skills."
            },
            {
                "question": f"Which approach best improves performance in {base_topic}?",
                "options": [
                    "Regular practice and review",
                    "Guessing without preparation",
                    "Avoiding feedback",
                    "Ignoring mistakes"
                ],
                "answer": "Regular practice and review",
                "explanation": "Consistent review and practice strengthen learning and retention."
            },
            {
                "question": f"Why is it important to review explanations in {base_topic}?",
                "options": [
                    "They clarify why an answer is correct",
                    "They make learning unnecessary",
                    "They remove all need for practice",
                    "They replace all study effort"
                ],
                "answer": "They clarify why an answer is correct",
                "explanation": "Explanations help learners understand the reasoning behind correct answers."
            },
            {
                "question": f"Which statement is most accurate about {base_topic}?",
                "options": [
                    "It requires understanding, application, and practice",
                    "It is only about memorizing one fact",
                    "It does not benefit from examples",
                    "It is unnecessary to review mistakes"
                ],
                "answer": "It requires understanding, application, and practice",
                "explanation": "Strong performance in a topic comes from understanding concepts and practicing them."
            },
            {
                "question": f"What should a learner do after getting a question wrong in {base_topic}?",
                "options": [
                    "Review the correct answer and learn why it was wrong",
                    "Ignore the mistake and move on",
                    "Repeat the same wrong approach",
                    "Assume the topic is not important"
                ],
                "answer": "Review the correct answer and learn why it was wrong",
                "explanation": "Learning from mistakes is essential for improvement and mastery."
            }
        ]

        for i in range(count):
            template = templates[i % len(templates)]
            question = {
                "question": template["question"],
                "options": template["options"],
                "answer": template["answer"],
                "explanation": template["explanation"]
            }
            questions.append(question)

        return questions[:count]

    def _generate_with_gemini(self, prompt):
        api_key = os.getenv("GEMINI_API_KEY")
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
        api_key = os.getenv("OPENAI_API_KEY")
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
