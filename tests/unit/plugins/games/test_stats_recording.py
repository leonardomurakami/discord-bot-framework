"""Tests for games plugin stats recording — award_points, process_angle_guess, record_rps_result."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from plugins.games.config import ANGLE_POINTS
from plugins.games.plugin import GamesPlugin
from tests.conftest import AsyncContextManager


@pytest.fixture
def games_plugin(mock_bot):
    """Create a GamesPlugin instance with a mock bot."""
    return GamesPlugin(mock_bot)


class TestAwardPointsRecording:
    """Test that award_points persists expected TriviaStats fields."""

    @pytest.mark.asyncio
    async def test_new_stats_created_on_first_play(self, games_plugin):
        """Test that a new TriviaStats record is created when none exists."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_achievements", new_callable=AsyncMock):
                await games_plugin.award_points(111, 222, 20, "medium", False, 3.0, is_correct=True)

        mock_session.add.assert_called_once()
        added_obj = mock_session.add.call_args.args[0]
        assert added_obj.user_id == 111
        assert added_obj.guild_id == 222
        # total_questions is incremented after creation
        assert added_obj.total_questions == 1
        assert added_obj.correct_answers == 1
        assert added_obj.medium_correct == 1

    @pytest.mark.asyncio
    async def test_total_questions_incremented(self, games_plugin):
        """Test that total_questions is incremented."""
        mock_stats = MagicMock()
        mock_stats.total_questions = 10
        mock_stats.correct_answers = 5
        mock_stats.total_points = 100
        mock_stats.easy_correct = 2
        mock_stats.medium_correct = 2
        mock_stats.hard_correct = 1
        mock_stats.current_streak = 3
        mock_stats.best_streak = 5
        mock_stats.fast_answers = 2
        mock_stats.hints_used = 0
        mock_stats.record_result = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_stats

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_achievements", new_callable=AsyncMock):
                await games_plugin.award_points(111, 222, 20, "medium", False, 3.0, is_correct=True)

        assert mock_stats.total_questions == 11

    @pytest.mark.asyncio
    async def test_correct_answer_increments_correct_and_points(self, games_plugin):
        """Test that a correct answer increments correct_answers, points, and difficulty breakdown."""
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
                await games_plugin.award_points(111, 222, 30, "hard", False, 3.0, is_correct=True)

        assert mock_stats.correct_answers == 1
        assert mock_stats.hard_correct == 1
        assert mock_stats.total_points >= 30  # base + streak bonus

    @pytest.mark.asyncio
    async def test_fast_answer_recorded(self, games_plugin):
        """Test that fast answers (≤5s) are tracked."""
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

        assert mock_stats.fast_answers == 1

    @pytest.mark.asyncio
    async def test_slow_answer_not_recorded_as_fast(self, games_plugin):
        """Test that answers taking >5s are NOT tracked as fast."""
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
                await games_plugin.award_points(111, 222, 10, "easy", False, 8.0, is_correct=True)

        assert mock_stats.fast_answers == 0

    @pytest.mark.asyncio
    async def test_hints_used_incremented(self, games_plugin):
        """Test that hints_used is incremented when a hint is used."""
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

        assert mock_stats.hints_used == 1

    @pytest.mark.asyncio
    async def test_achievement_check_fires(self, games_plugin):
        """Test that achievement check is called after stats are updated (when no hint used)."""
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
            with patch.object(games_plugin, "_check_achievements", new_callable=AsyncMock) as mock_check:
                await games_plugin.award_points(111, 222, 10, "easy", False, 3.0, is_correct=True)

        mock_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_achievement_check_skipped_with_hint(self, games_plugin):
        """Test that achievement check is NOT called when a hint is used."""
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
            with patch.object(games_plugin, "_check_achievements", new_callable=AsyncMock) as mock_check:
                await games_plugin.award_points(111, 222, 10, "easy", True, 3.0, is_correct=True)

        mock_check.assert_not_called()

    @pytest.mark.asyncio
    async def test_incorrect_answer_resets_streak(self, games_plugin):
        """Test that an incorrect answer resets the current streak."""
        mock_stats = MagicMock()
        mock_stats.total_questions = 5
        mock_stats.correct_answers = 3
        mock_stats.total_points = 60
        mock_stats.easy_correct = 1
        mock_stats.medium_correct = 1
        mock_stats.hard_correct = 1
        mock_stats.current_streak = 3
        mock_stats.best_streak = 5
        mock_stats.fast_answers = 2
        mock_stats.hints_used = 0
        mock_stats.record_result = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_stats

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_achievements", new_callable=AsyncMock):
                await games_plugin.award_points(111, 222, 0, "medium", False, 10.0, is_correct=False)

        assert mock_stats.current_streak == 0
        assert mock_stats.total_questions == 6
        # correct_answers should NOT increment for incorrect
        assert mock_stats.correct_answers == 3


class TestProcessAngleGuessRecording:
    """Test that process_angle_guess updates AngleGame and AngleStats on completion."""

    def _make_angle_mocks(self, target=90, guesses=None, points_eligible=True):
        """Create mock game, stats, session, and results for angle tests."""
        mock_game = MagicMock()
        mock_game.target_angle = target
        mock_game.guesses = guesses if guesses is not None else []
        mock_game.is_complete = False
        mock_game.won = False
        mock_game.points_awarded = 0
        mock_game.points_eligible = points_eligible

        mock_game_result = MagicMock()
        mock_game_result.scalars.return_value.first.return_value = mock_game

        mock_stats = MagicMock()
        mock_stats.total_games = 0
        mock_stats.wins = 0
        mock_stats.total_points = 0
        mock_stats.exact_wins = 0
        mock_stats.close_wins = 0
        mock_stats.current_win_streak = 0
        mock_stats.best_win_streak = 0

        mock_stats_result = MagicMock()
        mock_stats_result.scalars.return_value.first.return_value = mock_stats

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[mock_game_result, mock_stats_result])
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.add = MagicMock()

        return mock_game, mock_stats, mock_session

    @pytest.mark.asyncio
    async def test_exact_guess_awards_100_points(self, games_plugin):
        """Test that an exact guess (0° off) awards 100 points and completes the game."""
        mock_game, mock_stats, mock_session = self._make_angle_mocks(target=90, guesses=[])

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_angle_achievements", new_callable=AsyncMock):
                result = await games_plugin.process_angle_guess(111, 222, 90)

        assert result["is_complete"] is True
        assert result["won"] is True
        assert mock_game.points_awarded == ANGLE_POINTS["exact"]
        assert mock_stats.total_games == 1
        assert mock_stats.wins == 1
        assert mock_stats.total_points == ANGLE_POINTS["exact"]
        assert mock_stats.exact_wins == 1
        assert mock_stats.current_win_streak == 1
        assert mock_stats.best_win_streak == 1

    @pytest.mark.asyncio
    async def test_1_degree_off_does_not_complete(self, games_plugin):
        """Test that a guess 1° off does NOT complete the game (player can continue)."""
        mock_game, mock_stats, mock_session = self._make_angle_mocks(target=90, guesses=[])

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_angle_achievements", new_callable=AsyncMock):
                result = await games_plugin.process_angle_guess(111, 222, 91)

        assert result["is_complete"] is False
        assert result["won"] is False
        # Stats should NOT be updated since game is not complete
        assert mock_stats.total_games == 0

    @pytest.mark.asyncio
    async def test_2_degrees_off_does_not_complete(self, games_plugin):
        """Test that a guess 2° off does NOT complete the game."""
        mock_game, mock_stats, mock_session = self._make_angle_mocks(target=90, guesses=[])

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_angle_achievements", new_callable=AsyncMock):
                result = await games_plugin.process_angle_guess(111, 222, 92)

        assert result["is_complete"] is False
        assert result["won"] is False
        assert mock_stats.total_games == 0

    @pytest.mark.asyncio
    async def test_out_of_attempts_no_win(self, games_plugin):
        """Test that exhausting 4 attempts without a win marks the game complete with no points."""
        mock_game, mock_stats, mock_session = self._make_angle_mocks(target=90, guesses=[10, 20, 30])

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_angle_achievements", new_callable=AsyncMock):
                result = await games_plugin.process_angle_guess(111, 222, 40)

        assert result["is_complete"] is True
        assert result["won"] is False
        assert mock_game.points_awarded == 0
        assert mock_stats.total_games == 1
        assert mock_stats.wins == 0
        assert mock_stats.current_win_streak == 0
        assert mock_stats.total_points == 0

    @pytest.mark.asyncio
    async def test_exact_on_second_guess_counts_as_close_win(self, games_plugin):
        """Test that an exact match on the 2nd guess counts as close_wins (not exact_wins)."""
        mock_game, mock_stats, mock_session = self._make_angle_mocks(target=90, guesses=[50])

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_angle_achievements", new_callable=AsyncMock):
                result = await games_plugin.process_angle_guess(111, 222, 90)

        assert result["is_complete"] is True
        assert result["won"] is True
        assert mock_stats.wins == 1
        # exact_wins only when dist==0 AND len(guesses)==1; here len==2
        assert mock_stats.exact_wins == 0
        # Falls to elif dist <= 2 → close_wins
        assert mock_stats.close_wins == 1
        assert mock_stats.current_win_streak == 1

    @pytest.mark.asyncio
    async def test_angle_achievement_check_fires(self, games_plugin):
        """Test that angle achievement check fires on completion."""
        mock_game, mock_stats, mock_session = self._make_angle_mocks(target=90, guesses=[])

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_angle_achievements", new_callable=AsyncMock) as mock_check:
                await games_plugin.process_angle_guess(111, 222, 90)

        mock_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_angle_achievement_check_skipped_when_not_complete(self, games_plugin):
        """Test that angle achievement check does NOT fire when game is not complete."""
        mock_game, mock_stats, mock_session = self._make_angle_mocks(target=90, guesses=[])

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_angle_achievements", new_callable=AsyncMock) as mock_check:
                await games_plugin.process_angle_guess(111, 222, 91)

        mock_check.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_eligible_game_no_stats_update(self, games_plugin):
        """Test that a non-points-eligible game does not update stats."""
        mock_game, mock_stats, mock_session = self._make_angle_mocks(target=90, guesses=[], points_eligible=False)

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_angle_achievements", new_callable=AsyncMock):
                result = await games_plugin.process_angle_guess(111, 222, 90)

        assert result["is_complete"] is True
        assert result["won"] is True
        # points_eligible is False, so no stats update
        assert mock_stats.total_games == 0


class TestRecordRPSResult:
    """Test that record_rps_result updates RPSStats and triggers achievement checks."""

    def _make_rps_mocks(self, existing_stats=None):
        """Create mock stats and session for RPS tests."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = existing_stats

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        return mock_session

    @pytest.mark.asyncio
    async def test_win_increments_wins_and_streak(self, games_plugin):
        """Test that a win increments wins, current_win_streak, and per-move wins."""
        mock_stats = MagicMock()
        mock_stats.total_games = 0
        mock_stats.wins = 0
        mock_stats.losses = 0
        mock_stats.draws = 0
        mock_stats.rock_wins = 0
        mock_stats.paper_wins = 0
        mock_stats.scissors_wins = 0
        mock_stats.current_win_streak = 0
        mock_stats.best_win_streak = 0

        mock_session = self._make_rps_mocks(mock_stats)

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_rps_achievements", new_callable=AsyncMock):
                await games_plugin.record_rps_result(111, 222, "rock", "win")

        assert mock_stats.total_games == 1
        assert mock_stats.wins == 1
        assert mock_stats.rock_wins == 1
        assert mock_stats.current_win_streak == 1
        assert mock_stats.best_win_streak == 1

    @pytest.mark.asyncio
    async def test_paper_win_increments_paper_wins(self, games_plugin):
        """Test that a paper win increments paper_wins."""
        mock_stats = MagicMock()
        mock_stats.total_games = 0
        mock_stats.wins = 0
        mock_stats.losses = 0
        mock_stats.draws = 0
        mock_stats.rock_wins = 0
        mock_stats.paper_wins = 0
        mock_stats.scissors_wins = 0
        mock_stats.current_win_streak = 0
        mock_stats.best_win_streak = 0

        mock_session = self._make_rps_mocks(mock_stats)

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_rps_achievements", new_callable=AsyncMock):
                await games_plugin.record_rps_result(111, 222, "paper", "win")

        assert mock_stats.paper_wins == 1
        assert mock_stats.rock_wins == 0
        assert mock_stats.scissors_wins == 0

    @pytest.mark.asyncio
    async def test_scissors_win_increments_scissors_wins(self, games_plugin):
        """Test that a scissors win increments scissors_wins."""
        mock_stats = MagicMock()
        mock_stats.total_games = 0
        mock_stats.wins = 0
        mock_stats.losses = 0
        mock_stats.draws = 0
        mock_stats.rock_wins = 0
        mock_stats.paper_wins = 0
        mock_stats.scissors_wins = 0
        mock_stats.current_win_streak = 0
        mock_stats.best_win_streak = 0

        mock_session = self._make_rps_mocks(mock_stats)

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_rps_achievements", new_callable=AsyncMock):
                await games_plugin.record_rps_result(111, 222, "scissors", "win")

        assert mock_stats.scissors_wins == 1

    @pytest.mark.asyncio
    async def test_loss_increments_losses_and_resets_streak(self, games_plugin):
        """Test that a loss increments losses and resets the win streak."""
        mock_stats = MagicMock()
        mock_stats.total_games = 5
        mock_stats.wins = 3
        mock_stats.losses = 1
        mock_stats.draws = 1
        mock_stats.rock_wins = 2
        mock_stats.paper_wins = 1
        mock_stats.scissors_wins = 0
        mock_stats.current_win_streak = 2
        mock_stats.best_win_streak = 3

        mock_session = self._make_rps_mocks(mock_stats)

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_rps_achievements", new_callable=AsyncMock):
                await games_plugin.record_rps_result(111, 222, "paper", "lose")

        assert mock_stats.total_games == 6
        assert mock_stats.losses == 2
        assert mock_stats.current_win_streak == 0
        # best_win_streak should NOT change on a loss
        assert mock_stats.best_win_streak == 3

    @pytest.mark.asyncio
    async def test_draw_increments_draws_and_resets_streak(self, games_plugin):
        """Test that a draw increments draws and resets the win streak."""
        mock_stats = MagicMock()
        mock_stats.total_games = 5
        mock_stats.wins = 3
        mock_stats.losses = 1
        mock_stats.draws = 1
        mock_stats.rock_wins = 2
        mock_stats.paper_wins = 1
        mock_stats.scissors_wins = 0
        mock_stats.current_win_streak = 2
        mock_stats.best_win_streak = 3

        mock_session = self._make_rps_mocks(mock_stats)

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_rps_achievements", new_callable=AsyncMock):
                await games_plugin.record_rps_result(111, 222, "scissors", "draw")

        assert mock_stats.total_games == 6
        assert mock_stats.draws == 2
        assert mock_stats.current_win_streak == 0

    @pytest.mark.asyncio
    async def test_rps_achievement_check_fires(self, games_plugin):
        """Test that RPS achievement check fires after recording."""
        mock_stats = MagicMock()
        mock_stats.total_games = 0
        mock_stats.wins = 0
        mock_stats.losses = 0
        mock_stats.draws = 0
        mock_stats.rock_wins = 0
        mock_stats.paper_wins = 0
        mock_stats.scissors_wins = 0
        mock_stats.current_win_streak = 0
        mock_stats.best_win_streak = 0

        mock_session = self._make_rps_mocks(mock_stats)

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_rps_achievements", new_callable=AsyncMock) as mock_check:
                await games_plugin.record_rps_result(111, 222, "rock", "win")

        mock_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_new_stats_created_on_first_game(self, games_plugin):
        """Test that a new RPSStats record is created when none exists."""
        mock_session = self._make_rps_mocks(existing_stats=None)

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_rps_achievements", new_callable=AsyncMock):
                await games_plugin.record_rps_result(111, 222, "rock", "win")

        mock_session.add.assert_called_once()
        added_obj = mock_session.add.call_args.args[0]
        assert added_obj.user_id == 111
        assert added_obj.guild_id == 222

    @pytest.mark.asyncio
    async def test_win_streak_updates_best_streak(self, games_plugin):
        """Test that a win streak exceeding best_streak updates best_streak."""
        mock_stats = MagicMock()
        mock_stats.total_games = 3
        mock_stats.wins = 2
        mock_stats.losses = 1
        mock_stats.draws = 0
        mock_stats.rock_wins = 1
        mock_stats.paper_wins = 1
        mock_stats.scissors_wins = 0
        mock_stats.current_win_streak = 2
        mock_stats.best_win_streak = 2

        mock_session = self._make_rps_mocks(mock_stats)

        with patch.object(games_plugin, "db_session", return_value=AsyncContextManager(mock_session)):
            with patch.object(games_plugin, "_check_rps_achievements", new_callable=AsyncMock):
                await games_plugin.record_rps_result(111, 222, "scissors", "win")

        assert mock_stats.current_win_streak == 3
        assert mock_stats.best_win_streak == 3
