import base64
import hashlib
import json
import os
import random

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
        topic_lower = base_topic.lower()
        topic_banks = {
            "python": [
                ("Which Python data type stores key-value pairs?", "A dictionary", "Dictionaries map keys to values."),
                ("What does a Python list comprehension create?", "A new list", "A list comprehension builds a list from an iterable."),
                ("Which keyword defines a function in Python?", "def", "The def keyword starts a function definition."),
                ("What does len([10, 20, 30]) return?", "3", "The list contains three elements."),
                ("Which value represents the absence of a value in Python?", "None", "None is Python's null value."),
            ],
            "biology": [
                ("Which organelle is known as the powerhouse of a cell?", "Mitochondrion", "Mitochondria produce usable cellular energy."),
                ("What molecule carries genetic instructions?", "DNA", "DNA stores hereditary information."),
                ("Which process lets plants convert light into chemical energy?", "Photosynthesis", "Photosynthesis uses light to make chemical energy."),
                ("What is the basic unit of biological classification?", "Species", "A species groups organisms that can generally reproduce together."),
                ("Which blood cells help defend the body from infection?", "White blood cells", "White blood cells are part of the immune response."),
            ],
            "chemistry": [
                ("What is the chemical symbol for sodium?", "Na", "Na comes from the Latin name natrium."),
                ("What does a solution with pH 7 represent?", "Neutrality", "A pH of 7 is neutral under standard conditions."),
                ("Which particle has a negative electric charge?", "Electron", "Electrons carry negative charge."),
                ("What is the smallest unit of an element?", "Atom", "An atom retains the identity of an element."),
                ("Which bond involves sharing electron pairs?", "Covalent bond", "Covalent bonds share electrons between atoms."),
            ],
            "astronomy": [
                ("What is the closest star to Earth?", "The Sun", "The Sun is Earth's nearest star."),
                ("Which planet is famous for its visible ring system?", "Saturn", "Saturn has the most prominent ring system."),
                ("What force keeps planets in orbit around stars?", "Gravity", "Gravity provides the attraction needed for orbital motion."),
                ("What is a light-year a measure of?", "Distance", "A light-year is the distance light travels in one year."),
                ("Which galaxy contains our Solar System?", "The Milky Way", "Our Solar System lies in the Milky Way galaxy."),
            ],
            "physics": [
                ("What is the SI unit of force?", "Newton", "Force is measured in newtons in the SI system."),
                ("What does velocity describe?", "Speed with direction", "Velocity is a vector that includes speed and direction."),
                ("Which law explains inertia?", "Newton's first law", "Newton's first law states that objects resist changes in motion."),
                ("What form of energy is stored in a raised object?", "Gravitational potential energy", "Height in a gravitational field stores potential energy."),
                ("What happens to resistance in a typical metal as temperature rises?", "It increases", "Higher lattice vibrations usually impede electron flow."),
            ],
            "machine learning": [
                ("What is the purpose of a training dataset?", "To learn model patterns", "Training data provides examples used to fit model parameters."),
                ("What does overfitting mean?", "Performing well on training data but poorly on new data", "Overfit models fail to generalize."),
                ("Which task predicts a continuous numeric value?", "Regression", "Regression models estimate numeric outcomes."),
                ("Why is a validation set used?", "To tune choices before final testing", "Validation data helps select settings without using the test set."),
                ("What does a classification model predict?", "A category or class", "Classification assigns inputs to discrete labels."),
            ],
            "world history": [
                ("Which ancient civilization built the pyramids at Giza?", "Ancient Egypt", "The pyramids at Giza were built in ancient Egypt."),
                ("What was the main purpose of the Magna Carta?", "To limit royal power", "The Magna Carta established limits on the English monarch."),
                ("Which event began in 1789 in France?", "The French Revolution", "The French Revolution began in 1789."),
                ("What trade route connected East Asia and Europe?", "The Silk Road", "The Silk Road linked major regions through trade."),
                ("Which empire used Constantinople as its capital?", "The Byzantine Empire", "Constantinople was the Byzantine capital for centuries."),
            ],
            "web development": [
                ("Which language structures the content of a web page?", "HTML", "HTML defines the structure and content of web pages."),
                ("Which technology controls a page's visual presentation?", "CSS", "CSS defines layout, colors, and visual styling."),
                ("What does HTTP status 404 indicate?", "The resource was not found", "A 404 response means the requested resource is unavailable."),
                ("Which browser technology adds behavior to a page?", "JavaScript", "JavaScript enables interactive browser behavior."),
                ("What does a responsive layout adapt to?", "Different screen sizes", "Responsive design adjusts presentation for available space."),
            ],
        }
        topic_key = next((key for key in topic_banks if key in topic_lower), None)
        templates = topic_banks.get(topic_key, profiles.get(difficulty, profiles["medium"]))
        repeated_templates = (templates * max(1, (count + len(templates) - 1) // len(templates)))[:count]
        random.shuffle(repeated_templates)

        questions = []
        wrong_options_by_topic = {
            "python": ["A tuple", "A loop", "A module"],
            "biology": ["A tissue", "A hormone", "A mineral"],
            "chemistry": ["Proton", "Molecule", "Catalyst"],
            "astronomy": ["The Moon", "An asteroid", "A comet"],
            "physics": ["Joule", "Watt", "Pascal"],
            "machine learning": ["A database", "A compiler", "A web server"],
            "world history": ["The Roman Republic", "The Han Dynasty", "The Ottoman Empire"],
            "web development": ["SQL", "Python", "Git"],
        }
        wrong_options = wrong_options_by_topic.get(topic_key, [
            "Avoid the topic entirely",
            "Guess without checking the reasoning",
            "Memorize one answer and skip practice",
        ])

        for question_text, answer, explanation in repeated_templates:
            options = [answer] + wrong_options[:]
            random.shuffle(options)
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
