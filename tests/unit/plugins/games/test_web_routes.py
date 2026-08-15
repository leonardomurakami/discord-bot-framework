"""Tests for games plugin web routes — trivia, angle, RPS, leaderboards, stats."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plugins.games.web.routes import register_games_routes

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class MockAuth:
    """Mock DiscordAuth that always reports authenticated."""

    def __init__(self, authenticated: bool = True, user_id: int = 111111111):
        self._authenticated = authenticated
        self._user_id = user_id

    def is_authenticated(self, request) -> bool:
        return self._authenticated

    def get_current_user(self, request):
        if not self._authenticated:
            return None
        return {"user": {"id": str(self._user_id)}, "guilds": []}


@pytest.fixture
def mock_plugin():
    """Create a mock GamesPlugin with stubbed helpers."""
    plugin = MagicMock()
    plugin.session = None
    plugin._replay_games = {}

    # Auth setup
    mock_auth = MockAuth()
    mock_web_app = MagicMock()
    mock_web_app.auth = mock_auth
    plugin.web_panel = mock_web_app

    # Stub helpers
    plugin.fetch_trivia_question = AsyncMock(
        return_value={
            "question": "What is 2+2?",
            "correct_answer": "4",
            "incorrect_answers": ["3", "5", "6"],
            "all_answers": ["4", "3", "5", "6"],
            "category": "Math",
            "difficulty": "easy",
        }
    )
    plugin.award_points = AsyncMock()
    plugin.get_or_create_angle_game = AsyncMock(
        return_value={
            "target": 90,
            "guesses": [],
            "is_complete": False,
            "won": False,
            "points_awarded": 0,
            "points_eligible": True,
            "attempts_remaining": 4,
        }
    )
    plugin.process_angle_guess = AsyncMock(
        return_value={
            "target": 90,
            "guesses": [90],
            "is_complete": True,
            "won": True,
            "points_awarded": 100,
            "points_eligible": True,
            "attempts_remaining": 3,
        }
    )
    plugin.record_rps_result = AsyncMock()
    plugin.get_leaderboard = AsyncMock(
        return_value=[
            {"user_id": 111, "points": 500, "accuracy": 80.0, "streak": 10},
            {"user_id": 222, "points": 300, "accuracy": 60.0, "streak": 5},
        ]
    )
    plugin.get_trivia_stats = AsyncMock(return_value=None)
    plugin.get_angle_stats = AsyncMock(return_value=None)
    plugin.get_trivia_achievements = AsyncMock(return_value=[])
    plugin.get_angle_achievements = AsyncMock(return_value=[])
    plugin.get_rps_achievements = AsyncMock(return_value=[])
    plugin.get_rps_stats = AsyncMock(return_value=None)

    # render_plugin_template stub
    plugin.render_plugin_template = MagicMock(return_value=MagicMock())

    return plugin


@pytest.fixture
def app_and_plugin(mock_plugin):
    """Create a FastAPI app with games routes registered."""
    app = FastAPI()
    register_games_routes(app, mock_plugin)
    return app, mock_plugin


@pytest.fixture
def client(app_and_plugin):
    """Create a TestClient."""
    app, _ = app_and_plugin
    return TestClient(app)


# ---------------------------------------------------------------------------
# Section navigation tests
# ---------------------------------------------------------------------------


class TestSectionNavigation:
    """Test section navigation endpoints."""

    def test_section_play_authenticated(self, client, mock_plugin):
        """Test that the Play section loads for authenticated users."""
        resp = client.get("/plugin/games/api/section/play", params={"guild_id": "123"})
        assert resp.status_code == 200
        assert "Trivia" in resp.text
        assert "Angle Game" in resp.text
        assert "Rock Paper Scissors" in resp.text

    def test_section_leaderboards_authenticated(self, client):
        """Test that the Leaderboards section loads."""
        resp = client.get("/plugin/games/api/section/leaderboards", params={"guild_id": "123"})
        assert resp.status_code == 200
        assert "lb-sort" in resp.text or "leaderboard" in resp.text.lower()

    def test_section_stats_authenticated(self, client):
        """Test that the Stats section loads."""
        resp = client.get("/plugin/games/api/section/stats", params={"guild_id": "123"})
        assert resp.status_code == 200
        assert "stats-results" in resp.text

    def test_section_achievements_authenticated(self, client):
        """Test that the Achievements section loads."""
        resp = client.get("/plugin/games/api/section/achievements", params={"guild_id": "123"})
        assert resp.status_code == 200
        assert "ach-filter" in resp.text or "ach-results" in resp.text

    def test_section_unauthenticated(self, client, mock_plugin):
        """Test that unauthenticated requests return a login prompt."""
        mock_plugin.web_panel.web_app.auth = MockAuth(authenticated=False)
        resp = client.get("/plugin/games/api/section/play", params={"guild_id": "123"})
        assert resp.status_code == 200
        assert "log in" in resp.text.lower()

    def test_section_missing_guild(self, client):
        """Test that missing guild returns a select-a-server prompt."""
        resp = client.get("/plugin/games/api/section/play")
        assert resp.status_code == 200
        assert "select a server" in resp.text.lower()


# ---------------------------------------------------------------------------
# Trivia play tests
# ---------------------------------------------------------------------------


class TestTriviaRoutes:
    """Test trivia question fetch and answer endpoints."""

    def test_trivia_question_authenticated(self, client, mock_plugin):
        """Test that an authenticated request returns a question fragment."""
        resp = client.get("/plugin/games/api/trivia/question", params={"guild_id": "123"})
        assert resp.status_code == 200
        assert "What is 2+2?" in resp.text
        assert "games-answer-btn" in resp.text
        mock_plugin.fetch_trivia_question.assert_called_once()

    def test_trivia_question_unauthenticated(self, client, mock_plugin):
        """Test that unauthenticated requests return a login prompt."""
        mock_plugin.web_panel.web_app.auth = MockAuth(authenticated=False)
        resp = client.get("/plugin/games/api/trivia/question", params={"guild_id": "123"})
        assert resp.status_code == 200
        assert "log in" in resp.text.lower()
        mock_plugin.fetch_trivia_question.assert_not_called()

    def test_trivia_question_missing_guild(self, client, mock_plugin):
        """Test that missing guild returns a select-a-server prompt."""
        resp = client.get("/plugin/games/api/trivia/question")
        assert resp.status_code == 200
        assert "select a server" in resp.text.lower()
        mock_plugin.fetch_trivia_question.assert_not_called()

    def test_trivia_answer_correct(self, client, mock_plugin):
        """Test that a correct answer records stats and returns a success fragment."""
        resp = client.post(
            "/plugin/games/api/trivia/answer",
            data={
                "guild_id": "123",
                "answer": "4",
                "correct_answer": "4",
                "difficulty": "easy",
            },
        )
        assert resp.status_code == 200
        assert "Correct" in resp.text
        mock_plugin.award_points.assert_called_once()
        call_args = mock_plugin.award_points.call_args
        assert call_args.kwargs["is_correct"] is True

    def test_trivia_answer_incorrect(self, client, mock_plugin):
        """Test that an incorrect answer records stats and reveals the correct answer."""
        resp = client.post(
            "/plugin/games/api/trivia/answer",
            data={
                "guild_id": "123",
                "answer": "3",
                "correct_answer": "4",
                "difficulty": "easy",
            },
        )
        assert resp.status_code == 200
        assert "Incorrect" in resp.text
        assert "4" in resp.text  # correct answer revealed
        mock_plugin.award_points.assert_called_once()
        call_args = mock_plugin.award_points.call_args
        assert call_args.kwargs["is_correct"] is False

    def test_trivia_answer_unauthenticated(self, client, mock_plugin):
        """Test that unauthenticated answer requests don't record stats."""
        mock_plugin.web_panel.web_app.auth = MockAuth(authenticated=False)
        resp = client.post(
            "/plugin/games/api/trivia/answer",
            data={"guild_id": "123", "answer": "4", "correct_answer": "4"},
        )
        assert resp.status_code == 200
        assert "log in" in resp.text.lower()
        mock_plugin.award_points.assert_not_called()


# ---------------------------------------------------------------------------
# Angle game tests
# ---------------------------------------------------------------------------


class TestAngleRoutes:
    """Test angle start, guess, and image endpoints."""

    def test_angle_start_authenticated(self, client, mock_plugin):
        """Test that the start endpoint returns a game fragment."""
        resp = client.get("/plugin/games/api/angle/start", params={"guild_id": "123"})
        assert resp.status_code == 200
        assert "angle/image" in resp.text
        assert "guess" in resp.text.lower()
        mock_plugin.get_or_create_angle_game.assert_called_once()

    def test_angle_start_unauthenticated(self, client, mock_plugin):
        """Test that unauthenticated start returns a login prompt."""
        mock_plugin.web_panel.web_app.auth = MockAuth(authenticated=False)
        resp = client.get("/plugin/games/api/angle/start", params={"guild_id": "123"})
        assert resp.status_code == 200
        assert "log in" in resp.text.lower()
        mock_plugin.get_or_create_angle_game.assert_not_called()

    def test_angle_guess_authenticated(self, client, mock_plugin):
        """Test that the guess endpoint processes and returns updated feedback."""
        resp = client.post(
            "/plugin/games/api/angle/guess",
            data={"guild_id": "123", "guess": "90"},
        )
        assert resp.status_code == 200
        assert "angle/image" in resp.text
        mock_plugin.process_angle_guess.assert_called_once()

    def test_angle_guess_invalid(self, client, mock_plugin):
        """Test that an invalid guess returns an error."""
        resp = client.post(
            "/plugin/games/api/angle/guess",
            data={"guild_id": "123", "guess": "abc"},
        )
        assert resp.status_code == 200
        assert "whole number" in resp.text.lower()

    def test_angle_image_returns_png(self, client):
        """Test that the image endpoint returns PNG bytes with correct content type."""
        resp = client.get("/plugin/games/api/angle/image", params={"target": "90"})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert len(resp.content) > 0
        # PNG magic bytes
        assert resp.content[:4] == b"\x89PNG"

    def test_angle_image_clamps_target(self, client):
        """Test that the image endpoint clamps invalid target values."""
        resp = client.get("/plugin/games/api/angle/image", params={"target": "999"})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"

    def test_angle_guess_unauthenticated(self, client, mock_plugin):
        """Test that unauthenticated guess returns a login prompt."""
        mock_plugin.web_panel.web_app.auth = MockAuth(authenticated=False)
        resp = client.post(
            "/plugin/games/api/angle/guess",
            data={"guild_id": "123", "guess": "90"},
        )
        assert resp.status_code == 200
        assert "log in" in resp.text.lower()
        mock_plugin.process_angle_guess.assert_not_called()


# ---------------------------------------------------------------------------
# RPS tests
# ---------------------------------------------------------------------------


class TestRPSRoutes:
    """Test RPS play endpoint."""

    def test_rps_play_authenticated(self, client, mock_plugin):
        """Test that an authenticated request returns an outcome fragment and records stats."""
        with patch("plugins.games.web.routes.random.choice", return_value="rock"):
            resp = client.post(
                "/plugin/games/api/rps/play",
                data={"guild_id": "123", "choice": "rock"},
            )
        assert resp.status_code == 200
        assert "Rock" in resp.text
        mock_plugin.record_rps_result.assert_called_once()

    def test_rps_play_win(self, client, mock_plugin):
        """Test that a win outcome is displayed correctly."""
        with patch("plugins.games.web.routes.random.choice", return_value="scissors"):
            resp = client.post(
                "/plugin/games/api/rps/play",
                data={"guild_id": "123", "choice": "rock"},
            )
        assert resp.status_code == 200
        assert "win" in resp.text.lower()
        mock_plugin.record_rps_result.assert_called_once()
        call_args = mock_plugin.record_rps_result.call_args
        assert call_args.args[3] == "win"

    def test_rps_play_unauthenticated(self, client, mock_plugin):
        """Test that unauthenticated requests return a login prompt."""
        mock_plugin.web_panel.web_app.auth = MockAuth(authenticated=False)
        resp = client.post(
            "/plugin/games/api/rps/play",
            data={"guild_id": "123", "choice": "rock"},
        )
        assert resp.status_code == 200
        assert "log in" in resp.text.lower()
        mock_plugin.record_rps_result.assert_not_called()

    def test_rps_play_invalid_choice(self, client, mock_plugin):
        """Test that an invalid choice returns an error."""
        resp = client.post(
            "/plugin/games/api/rps/play",
            data={"guild_id": "123", "choice": "invalid"},
        )
        assert resp.status_code == 200
        assert "invalid" in resp.text.lower()

    def test_rps_play_again(self, client, mock_plugin):
        """Test that the result fragment includes play-again buttons."""
        with patch("plugins.games.web.routes.random.choice", return_value="rock"):
            resp = client.post(
                "/plugin/games/api/rps/play",
                data={"guild_id": "123", "choice": "rock"},
            )
        assert resp.status_code == 200
        assert "rps/play" in resp.text  # play-again buttons


# ---------------------------------------------------------------------------
# Leaderboards and stats tests
# ---------------------------------------------------------------------------


class TestLeaderboardsAndStatsRoutes:
    """Test leaderboards and stats endpoints."""

    def test_leaderboards_points(self, client, mock_plugin):
        """Test that the leaderboards endpoint returns ranked entries for points sort."""
        resp = client.get("/plugin/games/api/leaderboards", params={"guild_id": "123", "sort": "points"})
        assert resp.status_code == 200
        assert "Leaderboard" in resp.text
        assert "500" in resp.text  # points value

    def test_leaderboards_accuracy(self, client, mock_plugin):
        """Test that the accuracy sort returns ranked entries."""
        resp = client.get("/plugin/games/api/leaderboards", params={"guild_id": "123", "sort": "accuracy"})
        assert resp.status_code == 200
        assert "Leaderboard" in resp.text
        assert "80.0%" in resp.text

    def test_leaderboards_streak(self, client, mock_plugin):
        """Test that the streak sort returns ranked entries."""
        resp = client.get("/plugin/games/api/leaderboards", params={"guild_id": "123", "sort": "streak"})
        assert resp.status_code == 200
        assert "Leaderboard" in resp.text
        assert "10" in resp.text  # streak value

    def test_leaderboards_empty(self, client, mock_plugin):
        """Test that an empty leaderboard shows an informative empty state."""
        mock_plugin.get_leaderboard = AsyncMock(return_value=[])
        resp = client.get("/plugin/games/api/leaderboards", params={"guild_id": "123"})
        assert resp.status_code == 200
        assert "no trivia data" in resp.text.lower()

    def test_leaderboards_unauthenticated(self, client, mock_plugin):
        """Test that unauthenticated requests return a login prompt."""
        mock_plugin.web_panel.web_app.auth = MockAuth(authenticated=False)
        resp = client.get("/plugin/games/api/leaderboards", params={"guild_id": "123"})
        assert resp.status_code == 200
        assert "log in" in resp.text.lower()

    def test_stats_with_data(self, client, mock_plugin):
        """Test that the stats endpoint returns the current user's trivia and angle stats."""
        mock_trivia = MagicMock()
        mock_trivia.total_questions = 50
        mock_trivia.correct_answers = 40
        mock_trivia.accuracy = 80.0
        mock_trivia.total_points = 500
        mock_trivia.easy_correct = 10
        mock_trivia.medium_correct = 20
        mock_trivia.hard_correct = 10
        mock_trivia.current_streak = 5
        mock_trivia.best_streak = 10
        mock_trivia.fast_answers = 15
        mock_trivia.hints_used = 3

        mock_angle = MagicMock()
        mock_angle.total_games = 20
        mock_angle.wins = 10
        mock_angle.win_rate = 50.0
        mock_angle.total_points = 300
        mock_angle.exact_wins = 5
        mock_angle.close_wins = 3
        mock_angle.current_win_streak = 2
        mock_angle.best_win_streak = 5

        mock_plugin.get_trivia_stats = AsyncMock(return_value=mock_trivia)
        mock_plugin.get_angle_stats = AsyncMock(return_value=mock_angle)

        resp = client.get("/plugin/games/api/stats", params={"guild_id": "123"})
        assert resp.status_code == 200
        assert "Trivia Stats" in resp.text
        assert "Angle Stats" in resp.text
        assert "50" in resp.text  # total questions
        assert "20" in resp.text  # total games

    def test_stats_empty(self, client, mock_plugin):
        """Test that stats for a user who hasn't played shows an empty state."""
        mock_plugin.get_trivia_stats = AsyncMock(return_value=None)
        mock_plugin.get_angle_stats = AsyncMock(return_value=None)
        resp = client.get("/plugin/games/api/stats", params={"guild_id": "123"})
        assert resp.status_code == 200
        assert "haven" in resp.text.lower() or "play" in resp.text.lower()

    def test_stats_unauthenticated(self, client, mock_plugin):
        """Test that unauthenticated stats requests return a login prompt."""
        mock_plugin.web_panel.web_app.auth = MockAuth(authenticated=False)
        resp = client.get("/plugin/games/api/stats", params={"guild_id": "123"})
        assert resp.status_code == 200
        assert "log in" in resp.text.lower()
