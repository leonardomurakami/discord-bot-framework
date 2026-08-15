"""Tests for BotSettings AI-related fields."""

from config.settings import BotSettings


class TestAISettings:
    """Test AI plugin configuration fields on BotSettings."""

    def test_defaults(self, monkeypatch):
        """AI fields default correctly when no env vars are set."""
        # Ensure no AI env vars leak in from the host.
        for var in (
            "ACPBOX_URL",
            "AI_MODEL",
            "AI_API_KEY",
            "AI_SYSTEM_PROMPT",
            "AI_MAX_TOKENS",
            "AI_TEMPERATURE",
            "AI_MEMORY_TURNS",
            "AI_REQUEST_TIMEOUT",
        ):
            monkeypatch.delenv(var, raising=False)

        settings = BotSettings(
            discord_token="test-token",
            web_secret_key="test-secret",
            _env_file=None,
        )

        assert settings.acpbox_url is None
        assert settings.ai_model == "glm-5-2"
        assert settings.ai_api_key is None
        assert "helpful" in settings.ai_system_prompt.lower()
        assert settings.ai_max_tokens == 1000
        assert settings.ai_temperature == 0.7
        assert settings.ai_memory_turns == 10
        assert settings.ai_request_timeout == 30

    def test_loads_from_env(self, monkeypatch):
        """AI fields load from their environment variables."""
        monkeypatch.setenv("ACPBOX_URL", "http://acpbox.local:8080")
        monkeypatch.setenv("AI_MODEL", "gpt-test")
        monkeypatch.setenv("AI_API_KEY", "secret-key")
        monkeypatch.setenv("AI_SYSTEM_PROMPT", "You are a pirate.")
        monkeypatch.setenv("AI_MAX_TOKENS", "2048")
        monkeypatch.setenv("AI_TEMPERATURE", "0.5")
        monkeypatch.setenv("AI_MEMORY_TURNS", "5")
        monkeypatch.setenv("AI_REQUEST_TIMEOUT", "60")

        settings = BotSettings(
            discord_token="test-token",
            web_secret_key="test-secret",
            _env_file=None,
        )

        assert settings.acpbox_url == "http://acpbox.local:8080"
        assert settings.ai_model == "gpt-test"
        assert settings.ai_api_key == "secret-key"
        assert settings.ai_system_prompt == "You are a pirate."
        assert settings.ai_max_tokens == 2048
        assert settings.ai_temperature == 0.5
        assert settings.ai_memory_turns == 5
        assert settings.ai_request_timeout == 60

    def test_ai_in_default_enabled_plugins(self, monkeypatch):
        """The 'ai' plugin is included in the default enabled_plugins list."""
        for var in ("ENABLED_PLUGINS",):
            monkeypatch.delenv(var, raising=False)

        settings = BotSettings(
            discord_token="test-token",
            web_secret_key="test-secret",
            _env_file=None,
        )

        assert "ai" in settings.enabled_plugins
