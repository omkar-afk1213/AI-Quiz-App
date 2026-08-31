import unittest

from services.quiz_generator import QuizGenerator


class QuizDifficultyTest(unittest.TestCase):
    def test_generate_accepts_difficulty_and_returns_questions(self):
        questions = QuizGenerator.generate("Python Basics", 2, difficulty="easy")

        self.assertIsInstance(questions, list)
        self.assertEqual(len(questions), 2)
        for question in questions:
            self.assertIn("question", question)
            self.assertIn("options", question)
            self.assertEqual(len(question["options"]), 4)
            self.assertIn("answer", question)


if __name__ == "__main__":
    unittest.main()
