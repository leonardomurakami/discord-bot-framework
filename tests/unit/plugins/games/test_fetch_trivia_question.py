"""Tests for GamesPlugin.fetch_trivia_question helper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from plugins.games.plugin import GamesPlugin
from tests.conftest import AsyncContextManager


@pytest.fixture
def games_plugin(mock_bot):
    """Create a GamesPlugin instance with a mock bot."""
    return GamesPlugin(mock_bot)


class TestFetchTriviaQuestion:
    """Test the fetch_trivia_question helper."""

    @pytest.mark.asyncio
    async def test_api_success(self, games_plugin):
        """Test fetching a question from the API successfully."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "response_code": 0,
            "results": [
                {
                    "question": "What is 2+2?",
                    "correct_answer": "4",
                    "incorrect_answers": ["3", "5", "6"],
                    "category": "Math",
                    "difficulty": "easy",
                }
            ],
        }

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))
        games_plugin.session = mock_session

        result = await games_plugin.fetch_trivia_question(guild_id=123, difficulty="easy")

        assert result is not None
        assert result["question"] == "What is 2+2?"
        assert result["correct_answer"] == "4"
        assert result["category"] == "Math"
        assert result["difficulty"] == "easy"
        assert "4" in result["all_answers"]
        assert len(result["all_answers"]) == 4

    @pytest.mark.asyncio
    async def test_api_failure_falls_back_to_custom_questions(self, games_plugin):
        """Test that API failure falls back to custom guild questions."""
        mock_response = AsyncMock()
        mock_response.status = 500

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))
        games_plugin.session = mock_session

        custom_q = MagicMock()
        custom_q.to_dict.return_value = {
            "question": "Custom question?",
            "correct_answer": "Yes",
            "incorrect_answers": ["No", "Maybe", "Never"],
            "category": "Custom",
            "difficulty": "medium",
        }

        with patch.object(games_plugin, "get_custom_questions", new_callable=AsyncMock) as mock_get_custom:
            mock_get_custom.return_value = [custom_q]
            with patch("random.choice", return_value=custom_q):
                result = await games_plugin.fetch_trivia_question(guild_id=123)

        assert result is not None
        assert result["question"] == "Custom question?"
        assert result["correct_answer"] == "Yes"
        assert result["category"] == "Custom"

    @pytest.mark.asyncio
    async def test_no_custom_questions_falls_back_to_defaults(self, games_plugin):
        """Test that with no API and no custom questions, defaults are used."""
        games_plugin.session = None

        with patch.object(games_plugin, "get_custom_questions", new_callable=AsyncMock) as mock_get_custom:
            mock_get_custom.return_value = []
            with patch(
                "random.choice",
                return_value={
                    "question": "What is the capital of Japan?",
                    "correct_answer": "Tokyo",
                    "incorrect_answers": ["Osaka", "Kyoto", "Hiroshima"],
                    "category": "Geography",
                    "difficulty": "easy",
                },
            ):
                result = await games_plugin.fetch_trivia_question(guild_id=123)

        assert result is not None
        assert result["question"] == "What is the capital of Japan?"
        assert result["correct_answer"] == "Tokyo"
        assert result["category"] == "Geography"
        assert result["difficulty"] == "easy"
        assert len(result["all_answers"]) == 4

    @pytest.mark.asyncio
    async def test_returns_normalized_with_shuffled_answers(self, games_plugin):
        """Test that the returned dict has all_answers shuffled and text unescaped."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "response_code": 0,
            "results": [
                {
                    "question": "What is &lt;html&gt;?",
                    "correct_answer": "&amp;",
                    "incorrect_answers": ["&lt;", "&gt;", "&quot;"],
                    "category": "Computers",
                    "difficulty": "hard",
                }
            ],
        }

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))
        games_plugin.session = mock_session

        result = await games_plugin.fetch_trivia_question(guild_id=123)

        assert result is not None
        assert result["question"] == "What is <html>?"
        assert result["correct_answer"] == "&"
        assert result["incorrect_answers"] == ["<", ">", '"']
        assert result["all_answers"] == ["&", "<", ">", '"'] or len(result["all_answers"]) == 4
