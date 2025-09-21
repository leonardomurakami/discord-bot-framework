from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings

"""Configuration, API endpoints, and fallback content for the fun plugin."""


class FunSettings(BaseSettings):
    """Configuration for the Fun plugin."""

    # API endpoints
    joke_api_url: str = Field(
        default="https://v2.jokeapi.dev/joke/Programming,Miscellaneous?blacklistFlags=nsfw,religious,political,racist,sexist,explicit",
        description="API endpoint for jokes",
    )
    quote_api_url: str = Field(
        default="https://api.quotable.io/random?maxLength=150",
        description="API endpoint for quotes",
    )
    meme_primary_api_url: str = Field(
        default="https://meme-api.com/gimme",
        description="Primary meme API endpoint",
    )
    meme_secondary_api_url: str = Field(
        default="https://api.imgflip.com/get_memes",
        description="Secondary meme API endpoint",
    )
    fact_api_url: str = Field(
        default="https://uselessfacts.jsph.pl/random.json?language=en",
        description="API endpoint for facts",
    )
    trivia_api_url: str = Field(
        default="https://opentdb.com/api.php?amount=1&type=multiple",
        description="API endpoint for trivia questions",
    )

    # Dice game limits
    min_dice: int = Field(default=1, description="Minimum number of dice")
    max_dice: int = Field(default=20, description="Maximum number of dice")
    min_sides: int = Field(default=2, description="Minimum sides per die")
    max_sides: int = Field(default=1000, description="Maximum sides per die")

    # Random number limit
    random_number_limit: int = Field(
        default=10_000_000,
        description="Maximum value for random number generation",
    )

    # UI timeouts
    game_view_timeout_seconds: int = Field(
        default=30,
        description="Timeout for game views in seconds",
    )
    content_view_timeout_seconds: int = Field(
        default=300,  # 5 minutes
        description="Timeout for content views in seconds",
    )

    # HTTP request timeout
    api_request_timeout_seconds: int = Field(
        default=10,
        description="Timeout for API requests in seconds",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "FUN_"
        case_sensitive = False
        extra = "ignore"

    @property
    def api_endpoints(self) -> dict[str, str]:
        """Get API endpoints as a dictionary for backwards compatibility."""
        return {
            "joke": self.joke_api_url,
            "quote": self.quote_api_url,
            "meme_primary": self.meme_primary_api_url,
            "meme_secondary": self.meme_secondary_api_url,
            "fact": self.fact_api_url,
            "trivia": self.trivia_api_url,
        }

    @property
    def dice_limits(self) -> dict[str, int]:
        """Get dice limits as a dictionary for backwards compatibility."""
        return {
            "min_dice": self.min_dice,
            "max_dice": self.max_dice,
            "min_sides": self.min_sides,
            "max_sides": self.max_sides,
        }


# Plugin settings instance
fun_settings = FunSettings()

# Legacy constants for backwards compatibility
API_ENDPOINTS = fun_settings.api_endpoints
DICE_LIMITS = fun_settings.dice_limits
RANDOM_NUMBER_LIMIT = fun_settings.random_number_limit

DEFAULT_JOKES = [
    "Why don't scientists trust atoms? Because they make up everything!",
    "Why did the scarecrow win an award? He was outstanding in his field!",
    "Why don't eggs tell jokes? They'd crack each other up!",
    "What do you call a fake noodle? An impasta!",
    "Why did the math book look so sad? Because it was full of problems!",
]

DEFAULT_QUOTES = [
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ("Innovation distinguishes between a leader and a follower.", "Steve Jobs"),
    ("Life is what happens to you while you're busy making other plans.", "John Lennon"),
    ("The future belongs to those who believe in the beauty of their dreams.", "Eleanor Roosevelt"),
    ("It is during our darkest moments that we must focus to see the light.", "Aristotle"),
    ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Winston Churchill"),
    ("The only impossible journey is the one you never begin.", "Tony Robbins"),
    ("In the middle of difficulty lies opportunity.", "Albert Einstein"),
    ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
    ("The only limit to our realization of tomorrow will be our doubts of today.", "Franklin D. Roosevelt"),
    ("Do not go where the path may lead, go instead where there is no path and leave a trail.", "Ralph Waldo Emerson"),
    ("The way to get started is to quit talking and begin doing.", "Walt Disney"),
    ("Don't be afraid to give up the good to go for the great.", "John D. Rockefeller"),
    ("If you really look closely, most overnight successes took a long time.", "Steve Jobs"),
    ("The greatest glory in living lies not in never falling, but in rising every time we fall.", "Nelson Mandela"),
]

DEFAULT_FACTS = [
    "Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly edible.",
    "A single cloud can weigh more than a million pounds. Despite floating in the sky, clouds are made of water droplets that collectively have significant mass.",
    "Bananas are berries, but strawberries aren't. Botanically speaking, berries must have seeds inside their flesh.",
    "The shortest war in history lasted only 38-45 minutes. It was between Britain and Zanzibar in 1896.",
    "Octopuses have three hearts and blue blood. Two hearts pump blood to the gills, while the third pumps to the rest of the body.",
    "A group of flamingos is called a 'flamboyance.' Other collective nouns include a 'murder' of crows and a 'wisdom' of wombats.",
    "The human brain contains approximately 86 billion neurons, roughly the same number of stars in the Milky Way galaxy.",
    "Butterflies taste with their feet. They have chemoreceptors on their feet that help them identify suitable plants for laying eggs.",
    "The Great Wall of China isn't visible from space with the naked eye, contrary to popular belief.",
    "A day on Venus is longer than its year. Venus rotates so slowly that it takes longer to complete one rotation than to orbit the Sun.",
    "Sharks have been around longer than trees. Sharks appeared about 400 million years ago, while trees appeared around 350 million years ago.",
    "The dot over a lowercase 'i' or 'j' is called a tittle.",
    "Wombat poop is cube-shaped. This helps prevent it from rolling away and marks their territory more effectively.",
    "There are more possible games of chess than atoms in the observable universe.",
    "Sea otters hold hands while sleeping to prevent themselves from drifting apart.",
]

DEFAULT_TRIVIA_QUESTIONS = [
    {
        "question": "What is the capital of Japan?",
        "correct_answer": "Tokyo",
        "incorrect_answers": ["Osaka", "Kyoto", "Hiroshima"],
        "category": "Geography",
    },
    {
        "question": "Which planet is known as the Red Planet?",
        "correct_answer": "Mars",
        "incorrect_answers": ["Venus", "Jupiter", "Saturn"],
        "category": "Science",
    },
    {
        "question": "Who painted the Mona Lisa?",
        "correct_answer": "Leonardo da Vinci",
        "incorrect_answers": ["Pablo Picasso", "Vincent van Gogh", "Michelangelo"],
        "category": "Art",
    },
    {
        "question": "What is the largest mammal in the world?",
        "correct_answer": "Blue Whale",
        "incorrect_answers": ["Elephant", "Giraffe", "Hippopotamus"],
        "category": "Nature",
    },
    {
        "question": "In which year did World War II end?",
        "correct_answer": "1945",
        "incorrect_answers": ["1944", "1946", "1943"],
        "category": "History",
    },
]

DEFAULT_WYR_QUESTIONS = [
    ("Have the ability to fly", "Have the ability to become invisible"),
    ("Always have to sing rather than speak", "Always have to dance rather than walk"),
    ("Live in a world without music", "Live in a world without movies"),
    ("Be able to read minds", "Be able to see the future"),
    ("Have unlimited money", "Have unlimited time"),
    ("Only be able to whisper", "Only be able to shout"),
    ("Fight 100 duck-sized horses", "Fight 1 horse-sized duck"),
    ("Have taste buds in your fingers", "Have your tongue always taste like your least favorite food"),
    ("Be famous but poor", "Be unknown but rich"),
    ("Live underwater", "Live in space"),
    ("Have no arms", "Have no legs"),
    ("Be able to control fire", "Be able to control water"),
    ("Never use the internet again", "Never watch TV/movies again"),
    ("Have perfect memory", "Have perfect intuition"),
    ("Be stuck in traffic for 2 hours every day", "Always have slow internet"),
    ("Have hiccups for the rest of your life", "Feel like you need to sneeze but can't for the rest of your life"),
    ("Only be able to eat sweet foods", "Only be able to eat savory foods"),
    ("Be 3 feet tall", "Be 8 feet tall"),
    (
        "Have everything you eat taste like your favorite food",
        "Have everything you eat be your favorite food but taste terrible",
    ),
    ("Live in a world where everything is purple", "Live in a world where everything is silent"),
]

MOTIVATIONAL_EMOJIS = ["💪", "🌟", "✨", "🎯", "🚀", "💎", "🔥", "⭐"]
EDUCATIONAL_EMOJIS = ["🧠", "📚", "🔬", "🌟", "💡", "🎓", "🧪", "🔍"]

