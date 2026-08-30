from models.db import get_db


class PerformanceAnalyzer:
    @staticmethod
    def analyze(user_id):
        db = get_db()
        rows = db.execute(
            "SELECT topic, score, total FROM quiz_attempts WHERE user_id = ? ORDER BY taken_at DESC",
            (user_id,),
        ).fetchall()

        if not rows:
            return {
                "weak_topics": [],
                "strong_topics": [],
                "avg_score": 0.0,
                "total_attempts": 0,
                "recommendation": "Take a quiz to begin building your study profile.",
            }

        topic_scores = {}
        for row in rows:
            topic = row["topic"]
            percent = (row["score"] / row["total"]) * 100 if row["total"] else 0
            topic_scores.setdefault(topic, []).append(percent)

        weak_topics = []
        strong_topics = []
        recommendations = []

        for topic, scores in topic_scores.items():
            avg = sum(scores) / len(scores)
            if avg < 60:
                weak_topics.append(topic)
                recommendations.append(topic)
            elif avg >= 80:
                strong_topics.append(topic)

        total_attempts = len(rows)
        avg_score = sum((row["score"] / row["total"]) * 100 if row["total"] else 0 for row in rows) / total_attempts

        if recommendations:
            recommendation = f"Focus more on {', '.join(recommendations[:2])} and review the concepts you miss most often."
        elif strong_topics:
            recommendation = f"You are strong in {', '.join(strong_topics[:2])}. Keep building on that momentum."
        else:
            recommendation = "Keep practicing and try a new topic to strengthen your overall understanding."

        return {
            "weak_topics": weak_topics,
            "strong_topics": strong_topics,
            "avg_score": round(avg_score, 2),
            "total_attempts": total_attempts,
            "recommendation": recommendation,
        }
