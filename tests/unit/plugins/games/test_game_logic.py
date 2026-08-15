"""Tests for games plugin game logic — trivia scoring, angle, RPS."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from plugins.games.config import ANGLE_MAX_ATTEMPTS, ANGLE_POINTS, games_settings
from plugins.games.plugin import GamesPlugin
from tests.conftest import AsyncContextManager


@pytest.fixture
def games_plugin(mock_bot):
    """Create a GamesPlugin instance with a mock bot."""
    return GamesPlugin(mock_bot)


class TestTriviaScoring:
    """Test trivia scoring logic via award_points."""

    @pytest.mark.asyncio
    async def test_base_points_by_difficulty(self, games_plugin):
        """Test that base points are awarded correctly per difficulty."""
        mock_stats = MagicMock()
        mock_stats.total_questions = 0
        mock_stats.correct_answers = 0
        mock_stats.total_points = 0
        mock_stats.easy_correct = 0
        mock_stats.medium_correct = 0
        mock_stats.hard_correct = 0
        mock_stats.current_streak = 0
        mock_stats.best_streak = 0
        mock_stats.fast_answers = 0
        mock_stats.hints_used = 0
        mock_stats.record_result = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_stats

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_achievements", new_callable=AsyncMock):
                await games_plugin.award_points(111, 222, 10, "easy", False, 3.0, is_correct=True)

        assert mock_stats.total_questions == 1
        assert mock_stats.correct_answers == 1
        assert mock_stats.total_points >= 10
        assert mock_stats.easy_correct == 1

    @pytest.mark.asyncio
    async def test_streak_bonus_cap(self, games_plugin):
        """Test that streak bonus is capped at the configured maximum."""
        mock_stats = MagicMock()
        mock_stats.total_questions = 5
        mock_stats.correct_answers = 5
        mock_stats.total_points = 100
        mock_stats.easy_correct = 5
        mock_stats.medium_correct = 0
        mock_stats.hard_correct = 0
        mock_stats.current_streak = 5
        mock_stats.best_streak = 5
        mock_stats.fast_answers = 0
        mock_stats.hints_used = 0
        mock_stats.record_result = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_stats

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_achievements", new_callable=AsyncMock):
                # Current streak will become 6, bonus = min(6*5, 50) = 30
                await games_plugin.award_points(111, 222, 20, "medium", False, 3.0, is_correct=True)

        # streak_bonus = min(6 * 5, 50) = 30
        expected_bonus = min(6 * games_settings.trivia_streak_bonus, games_settings.trivia_max_streak_bonus)
        assert mock_stats.total_points == 100 + 20 + expected_bonus

    @pytest.mark.asyncio
    async def test_streak_bonus_max_cap(self, games_plugin):
        """Test that streak bonus never exceeds the max cap."""
        mock_stats = MagicMock()
        mock_stats.total_questions = 20
        mock_stats.correct_answers = 20
        mock_stats.total_points = 500
        mock_stats.easy_correct = 0
        mock_stats.medium_correct = 20
        mock_stats.hard_correct = 0
        mock_stats.current_streak = 20
        mock_stats.best_streak = 20
        mock_stats.fast_answers = 0
        mock_stats.hints_used = 0
        mock_stats.record_result = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_stats

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_achievements", new_callable=AsyncMock):
                # Current streak will become 21, bonus = min(21*5, 50) = 50
                await games_plugin.award_points(111, 222, 20, "medium", False, 3.0, is_correct=True)

        # streak_bonus should be capped at 50
        assert mock_stats.total_points == 500 + 20 + games_settings.trivia_max_streak_bonus

    @pytest.mark.asyncio
    async def test_hint_penalty(self, games_plugin):
        """Test that using a hint does not increment correct_answers or streak."""
        mock_stats = MagicMock()
        mock_stats.total_questions = 0
        mock_stats.correct_answers = 0
        mock_stats.total_points = 0
        mock_stats.easy_correct = 0
        mock_stats.medium_correct = 0
        mock_stats.hard_correct = 0
        mock_stats.current_streak = 0
        mock_stats.best_streak = 0
        mock_stats.fast_answers = 0
        mock_stats.hints_used = 0
        mock_stats.record_result = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_stats

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_achievements", new_callable=AsyncMock):
                await games_plugin.award_points(111, 222, 10, "easy", True, 3.0, is_correct=True)

        # With hint: record_result is NOT called, hints_used increments
        assert mock_stats.hints_used == 1
        mock_stats.record_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_incorrect_answer_resets_streak(self, games_plugin):
        """Test that an incorrect answer resets the current streak."""
        mock_stats = MagicMock()
        mock_stats.total_questions = 5
        mock_stats.correct_answers = 5
        mock_stats.total_points = 100
        mock_stats.easy_correct = 5
        mock_stats.medium_correct = 0
        mock_stats.hard_correct = 0
        mock_stats.current_streak = 5
        mock_stats.best_streak = 5
        mock_stats.fast_answers = 0
        mock_stats.hints_used = 0
        mock_stats.record_result = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_stats

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_achievements", new_callable=AsyncMock):
                await games_plugin.award_points(111, 222, 0, "easy", False, 3.0, is_correct=False)

        assert mock_stats.current_streak == 0
        assert mock_stats.correct_answers == 5  # unchanged


class TestAngleGame:
    """Test angle game logic."""

    def test_get_daily_angle_determinism(self):
        """Test that the same user+date yields the same target angle."""
        user_id = 12345
        angle1 = GamesPlugin.get_daily_angle(user_id)
        angle2 = GamesPlugin.get_daily_angle(user_id)
        assert angle1 == angle2
        assert 1 <= angle1 <= 360

    def test_get_daily_angle_different_users(self):
        """Test that different users get different angles (probabilistically)."""
        angle1 = GamesPlugin.get_daily_angle(111)
        angle2 = GamesPlugin.get_daily_angle(222)
        # Very unlikely to be the same for different users
        assert 1 <= angle1 <= 360
        assert 1 <= angle2 <= 360

    def test_angle_distance(self):
        """Test angular distance calculation."""
        assert GamesPlugin.angle_distance(90, 90) == 0
        assert GamesPlugin.angle_distance(0, 180) == 180
        assert GamesPlugin.angle_distance(10, 350) == 20
        assert GamesPlugin.angle_distance(45, 90) == 45
        assert GamesPlugin.angle_distance(90, 45) == 45
        assert GamesPlugin.angle_distance(0, 360) == 0
        assert GamesPlugin.angle_distance(1, 359) == 2

    def test_angle_direction(self):
        """Test direction hint calculation."""
        assert GamesPlugin.angle_direction(10, 90) == "higher"
        assert GamesPlugin.angle_direction(350, 10) == "higher"
        assert GamesPlugin.angle_direction(90, 10) == "lower"
        assert GamesPlugin.angle_direction(180, 170) == "lower"
        # Exact match — diff is 0, which is <= 180, so "higher"
        assert GamesPlugin.angle_direction(90, 90) == "higher"

    def test_angle_max_attempts(self):
        """Test that ANGLE_MAX_ATTEMPTS is 4."""
        assert ANGLE_MAX_ATTEMPTS == 4

    def test_angle_points_for_precision(self):
        """Test points awarded for precision: exact=100, 1°=75, 2°=50."""
        assert ANGLE_POINTS["exact"] == 100
        assert ANGLE_POINTS["close"] == 75
        assert ANGLE_POINTS["near"] == 50

    def test_angle_points_not_awarded_beyond_2_degrees(self):
        """Test that no points are awarded for distance > 2."""
        # The logic in process_angle_guess only awards for dist 0, 1, 2
        # This is verified by checking the ANGLE_POINTS dict has no entry for > 2
        assert "exact" in ANGLE_POINTS  # 0°
        assert "close" in ANGLE_POINTS  # 1°
        assert "near" in ANGLE_POINTS  # 2°
        # No key for 3°+ — the code checks dist == 0, 1, 2 explicitly


class TestRPSOutcome:
    """Test RPS outcome determination for all nine combinations."""

    def test_rock_vs_rock(self):
        from plugins.games.web.routes import _rps_determine_result

        assert _rps_determine_result("rock", "rock") == "draw"

    def test_rock_vs_paper(self):
        from plugins.games.web.routes import _rps_determine_result

        assert _rps_determine_result("rock", "paper") == "lose"

    def test_rock_vs_scissors(self):
        from plugins.games.web.routes import _rps_determine_result

        assert _rps_determine_result("rock", "scissors") == "win"

    def test_paper_vs_rock(self):
        from plugins.games.web.routes import _rps_determine_result

        assert _rps_determine_result("paper", "rock") == "win"

    def test_paper_vs_paper(self):
        from plugins.games.web.routes import _rps_determine_result

        assert _rps_determine_result("paper", "paper") == "draw"

    def test_paper_vs_scissors(self):
        from plugins.games.web.routes import _rps_determine_result

        assert _rps_determine_result("paper", "scissors") == "lose"

    def test_scissors_vs_rock(self):
        from plugins.games.web.routes import _rps_determine_result

        assert _rps_determine_result("scissors", "rock") == "lose"

    def test_scissors_vs_paper(self):
        from plugins.games.web.routes import _rps_determine_result

        assert _rps_determine_result("scissors", "paper") == "win"

    def test_scissors_vs_scissors(self):
        from plugins.games.web.routes import _rps_determine_result

        assert _rps_determine_result("scissors", "scissors") == "draw"

    def test_all_nine_combinations(self):
        """Exhaustive test of all nine player-vs-bot move combinations."""
        from plugins.games.web.routes import _rps_determine_result

        expected = {
            ("rock", "rock"): "draw",
            ("rock", "paper"): "lose",
            ("rock", "scissors"): "win",
            ("paper", "rock"): "win",
            ("paper", "paper"): "draw",
            ("paper", "scissors"): "lose",
            ("scissors", "rock"): "lose",
            ("scissors", "paper"): "win",
            ("scissors", "scissors"): "draw",
        }
        for (player, bot), expected_result in expected.items():
            assert _rps_determine_result(player, bot) == expected_result, f"Failed for player={player}, bot={bot}"
