import re
import json

from services.ai_service import AIService


class QuizGenerator:
    @staticmethod
    def generate(topic, count):
        ai = AIService()
        questions = ai.generate_questions(topic, count)
        cleaned = []
        for item in questions:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question", "")).strip()
            options = item.get("options")
            answer = str(item.get("answer", "")).strip()
            explanation = str(item.get("explanation", "")).strip()
            if not question or not isinstance(options, list) or len(options) != 4:
                continue
            cleaned.append({
                "question": question,
                "options": [str(opt).strip() for opt in options],
                "answer": answer,
                "explanation": explanation,
            })
        if not cleaned:
            raise ValueError("No valid questions were returned by the AI service.")
        return cleaned[:count]
