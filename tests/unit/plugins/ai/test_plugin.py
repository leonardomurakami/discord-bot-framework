"""Tests for the AIPlugin lifecycle (on_load/on_unload, soft-fail behavior)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from plugins.ai.plugin import AIPlugin


class TestAIPluginLifecycle:
    def test_plugin_creation(self, mock_bot):
        plugin = AIPlugin(mock_bot)
        assert plugin.session is None
        assert plugin.bot == mock_bot

    @pytest.mark.asyncio
    async def test_on_load_creates_session_when_configured(self, mock_bot):
        plugin = AIPlugin(mock_bot)
        with (
            patch("plugins.ai.plugin.settings") as mock_settings,
            patch("plugins.ai.plugin.aiohttp.ClientSession") as mock_session_cls,
        ):
            mock_settings.acpbox_url = "http://acpbox.local:8080"
            mock_settings.ai_model = "gpt-test"
            mock_settings.ai_request_timeout = 30
            await plugin.on_load()
            mock_session_cls.assert_called_once()
            assert plugin.session is not None

    @pytest.mark.asyncio
    async def test_on_load_soft_fails_when_acpbox_url_unset(self, mock_bot):
        plugin = AIPlugin(mock_bot)
        with (
            patch("plugins.ai.plugin.settings") as mock_settings,
            patch("plugins.ai.plugin.aiohttp.ClientSession") as mock_session_cls,
        ):
            mock_settings.acpbox_url = None
            mock_settings.ai_model = "gpt-test"
            await plugin.on_load()
            mock_session_cls.assert_not_called()
            assert plugin.session is None

    @pytest.mark.asyncio
    async def test_on_load_creates_session_with_default_model(self, mock_bot):
        """Session is created when acpbox_url is set, even if ai_model uses its default."""
        plugin = AIPlugin(mock_bot)
        with (
            patch("plugins.ai.plugin.settings") as mock_settings,
            patch("plugins.ai.plugin.aiohttp.ClientSession") as mock_session_cls,
        ):
            mock_settings.acpbox_url = "http://acpbox.local:8080"
            mock_settings.ai_model = "glm-5-2"
            mock_settings.ai_request_timeout = 30
            await plugin.on_load()
            mock_session_cls.assert_called_once()
            assert plugin.session is not None

    @pytest.mark.asyncio
    async def test_on_unload_closes_session(self, mock_bot):
        plugin = AIPlugin(mock_bot)
        mock_session = AsyncMock()
        plugin.session = mock_session
        await plugin.on_unload()
        mock_session.close.assert_awaited_once()
        assert plugin.session is None

    @pytest.mark.asyncio
    async def test_on_unload_noop_when_session_none(self, mock_bot):
        plugin = AIPlugin(mock_bot)
        plugin.session = None
        # Should not raise.
        await plugin.on_unload()
        assert plugin.session is None

    def test_plugin_metadata_declares_permissions(self):
        from plugins.ai import PLUGIN_METADATA

        assert "basic.ai.chat" in PLUGIN_METADATA["permissions"]
        assert "basic.ai.clear" in PLUGIN_METADATA["permissions"]

    def test_setup_factory_returns_plugin(self, mock_bot):
        from plugins.ai import setup

        plugin = setup(mock_bot)
        assert isinstance(plugin, AIPlugin)
