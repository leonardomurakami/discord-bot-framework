"""Tests for the WouldYouRatherView."""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_view_context():
    """Create a mock miru.ViewContext for testing view callbacks."""
    ctx = MagicMock()
    ctx.user = MagicMock()
    ctx.user.id = 111111
    ctx.respond = AsyncMock()
    ctx.edit_response = AsyncMock()
    return ctx


class TestWouldYouRatherView:
    """Test WouldYouRatherView functionality."""

    def test_view_instantiation(self):
        """Test that WouldYouRatherView instantiates with correct buttons."""
        from plugins.fun.views import WouldYouRatherView

        view = WouldYouRatherView("optA", "optB")

        assert view.option_a == "optA"
        assert view.option_b == "optB"
        assert view.votes_a == set()
        assert view.votes_b == set()

        # Should have two buttons
        assert len(view.children) == 2

        button_a = view.children[0]
        button_b = view.children[1]

        assert button_a.label == "Option A"
        assert button_a.emoji == "🅰️"
        assert button_b.label == "Option B"
        assert button_b.emoji == "🅱️"

    @pytest.mark.asyncio
    async def test_vote_option_a(self, mock_view_context):
        """Test voting for option A updates results."""
        from plugins.fun.views import WouldYouRatherView

        view = WouldYouRatherView("optA", "optB")

        await view.vote_option_a(mock_view_context)

        assert 111111 in view.votes_a
        assert 111111 not in view.votes_b
        mock_view_context.respond.assert_called_once()
        mock_view_context.edit_response.assert_called_once()

        # Check the embed passed to edit_response
        call_kwargs = mock_view_context.edit_response.call_args.kwargs
        embed = call_kwargs.get("embed")
        assert embed is not None
        assert embed.title == "🤔 Would You Rather... (Live Results)"

        # Check fields show 100% for A
        field_a = embed.fields[0]
        assert "optA" in field_a.value
        assert "100.0%" in field_a.value
        assert "1 votes" in field_a.value

        field_b = embed.fields[1]
        assert "optB" in field_b.value
        assert "0.0%" in field_b.value

        # Footer should show 1 total vote
        assert "Total votes: 1" in embed.footer.text

    @pytest.mark.asyncio
    async def test_mixed_votes_percentages(self, mock_view_context):
        """Test percentage calculation with mixed votes (3 for A, 1 for B)."""
        from plugins.fun.views import WouldYouRatherView

        view = WouldYouRatherView("optA", "optB")

        # Simulate 3 votes for A and 1 for B
        view.votes_a = {1, 2, 3}
        view.votes_b = {4}

        await view._update_results(mock_view_context)

        call_kwargs = mock_view_context.edit_response.call_args.kwargs
        embed = call_kwargs.get("embed")
        assert embed is not None

        field_a = embed.fields[0]
        assert "75.0%" in field_a.value
        assert "3 votes" in field_a.value

        field_b = embed.fields[1]
        assert "25.0%" in field_b.value
        assert "1 votes" in field_b.value

        assert "Total votes: 4" in embed.footer.text

    @pytest.mark.asyncio
    async def test_toggle_vote_off(self, mock_view_context):
        """Test that voting for the same option again toggles the vote off."""
        from plugins.fun.views import WouldYouRatherView

        view = WouldYouRatherView("optA", "optB")

        # First vote for A
        await view.vote_option_a(mock_view_context)
        assert 111111 in view.votes_a

        # Vote for A again to toggle off
        await view.vote_option_a(mock_view_context)

        assert 111111 not in view.votes_a
        assert 111111 not in view.votes_b

        # Results should show zero total votes with equal percentages
        call_kwargs = mock_view_context.edit_response.call_args.kwargs
        embed = call_kwargs.get("embed")
        assert embed is not None

        field_a = embed.fields[0]
        assert "0.0%" in field_a.value
        assert "0 votes" in field_a.value

        field_b = embed.fields[1]
        assert "0.0%" in field_b.value
        assert "0 votes" in field_b.value

        assert "Total votes: 0" in embed.footer.text
