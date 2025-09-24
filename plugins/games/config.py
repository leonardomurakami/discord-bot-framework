from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings

"""Configuration and settings for the games plugin."""


class GamesSettings(BaseSettings):
    """Configuration for the Games plugin."""

    # API endpoints
    trivia_api_url: str = Field(
        default="https://opentdb.com/api.php?amount=1&type=multiple",
        description="API endpoint for trivia questions",
    )

    # Trivia game settings
    trivia_timeout_seconds: int = Field(
        default=30,
        description="Timeout for trivia questions in seconds",
    )
    trivia_hint_penalty: float = Field(
        default=0.5,
        description="Point multiplier when using hints (0.0-1.0)",
    )
    trivia_time_bonus_threshold: int = Field(
        default=10,
        description="Seconds threshold for time bonus points",
    )
    trivia_time_bonus_multiplier: float = Field(
        default=1.5,
        description="Multiplier for time bonus questions",
    )

    # Scoring system
    trivia_base_points: dict[str, int] = Field(
        default={
            "easy": 10,
            "medium": 20,
            "hard": 30,
        },
        description="Base points for each difficulty level",
    )
    trivia_streak_bonus: int = Field(
        default=5,
        description="Bonus points per consecutive correct answer",
    )
    trivia_max_streak_bonus: int = Field(
        default=50,
        description="Maximum streak bonus points",
    )

    # Question management
    max_custom_questions_per_guild: int = Field(
        default=1000,
        description="Maximum custom questions per guild",
    )
    bulk_import_max_questions: int = Field(
        default=100,
        description="Maximum questions in a single bulk import",
    )

    # HTTP request timeout
    api_request_timeout_seconds: int = Field(
        default=10,
        description="Timeout for API requests in seconds",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "GAMES_"
        case_sensitive = False
        extra = "ignore"


# Plugin settings instance
games_settings = GamesSettings()

# Trivia categories mapping (from Open Trivia Database)
TRIVIA_CATEGORIES = {
    "general": 9,
    "books": 10,
    "film": 11,
    "music": 12,
    "musicals": 13,
    "television": 14,
    "games": 15,
    "boardgames": 16,
    "science": 17,
    "computers": 18,
    "math": 19,
    "mythology": 20,
    "sports": 21,
    "geography": 22,
    "history": 23,
    "politics": 24,
    "art": 25,
    "celebrities": 26,
    "animals": 27,
    "vehicles": 28,
    "comics": 29,
    "gadgets": 30,
    "anime": 31,
    "cartoons": 32,
}

# Difficulty levels
TRIVIA_DIFFICULTIES = ["easy", "medium", "hard"]

# Default fallback questions
DEFAULT_TRIVIA_QUESTIONS = [
    {
        "question": "What is the capital of Japan?",
        "correct_answer": "Tokyo",
        "incorrect_answers": ["Osaka", "Kyoto", "Hiroshima"],
        "category": "Geography",
        "difficulty": "easy",
    },
    {
        "question": "Which planet is known as the Red Planet?",
        "correct_answer": "Mars",
        "incorrect_answers": ["Venus", "Jupiter", "Saturn"],
        "category": "Science",
        "difficulty": "easy",
    },
    {
        "question": "Who painted the Mona Lisa?",
        "correct_answer": "Leonardo da Vinci",
        "incorrect_answers": ["Pablo Picasso", "Vincent van Gogh", "Michelangelo"],
        "category": "Art",
        "difficulty": "medium",
    },
    {
        "question": "What is the largest mammal in the world?",
        "correct_answer": "Blue Whale",
        "incorrect_answers": ["Elephant", "Giraffe", "Hippopotamus"],
        "category": "Nature",
        "difficulty": "easy",
    },
    {
        "question": "In which year did World War II end?",
        "correct_answer": "1945",
        "incorrect_answers": ["1944", "1946", "1943"],
        "category": "History",
        "difficulty": "medium",
    },
]

# Achievement definitions
TRIVIA_ACHIEVEMENTS = {
    "first_correct": {
        "name": "First Steps",
        "description": "Answer your first trivia question correctly",
        "emoji": "🎯",
        "requirement": {"type": "correct_answers", "value": 1},
    },
    "trivia_novice": {
        "name": "Trivia Novice",
        "description": "Answer 10 trivia questions correctly",
        "emoji": "📚",
        "requirement": {"type": "correct_answers", "value": 10},
    },
    "trivia_expert": {
        "name": "Trivia Expert",
        "description": "Answer 100 trivia questions correctly",
        "emoji": "🧠",
        "requirement": {"type": "correct_answers", "value": 100},
    },
    "streak_master": {
        "name": "Streak Master",
        "description": "Get a streak of 10 correct answers",
        "emoji": "🔥",
        "requirement": {"type": "streak", "value": 10},
    },
    "speed_demon": {
        "name": "Speed Demon",
        "description": "Answer 20 questions in under 5 seconds",
        "emoji": "⚡",
        "requirement": {"type": "fast_answers", "value": 20},
    },
    "hard_mode": {
        "name": "Hard Mode",
        "description": "Answer 50 hard difficulty questions correctly",
        "emoji": "💪",
        "requirement": {"type": "hard_correct", "value": 50},
    },
    "category_master": {
        "name": "Category Master",
        "description": "Get 25 correct answers in a single category",
        "emoji": "🏆",
        "requirement": {"type": "category_mastery", "value": 25},
    },
    "high_scorer": {
        "name": "High Scorer",
        "description": "Reach 1000 total points",
        "emoji": "💎",
        "requirement": {"type": "total_points", "value": 1000},
    },
}

# Embed colors
EMBED_COLORS = {
    "trivia": 0x9932CC,
    "success": 0x00FF00,
    "error": 0xFF0000,
    "info": 0x3498DB,
    "warning": 0xFFD700,
    "achievement": 0xFF6B35,
}

# Emojis
DIFFICULTY_EMOJIS = {
    "easy": "🟢",
    "medium": "🟡",
    "hard": "🔴",
}

GAME_EMOJIS = ["🎮", "🎯", "🧠", "🎲", "🏆", "⭐", "🔥", "💎"]
