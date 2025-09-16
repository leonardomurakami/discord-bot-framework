"""Tests for bot/plugins/commands/decorators.py"""


import hikari

from bot.plugins.commands.argument_types import CommandArgument
from bot.plugins.commands.decorators import command


class TestCommandDecorator:
    """Test command decorator functionality."""

    def test_basic_command_creation(self):
        """Test creating a basic command with minimal parameters."""

        @command(name="test", description="Test command")
        async def test_func():
            return "success"

        # Check that metadata was stored
        assert hasattr(test_func, "_unified_command")
        metadata = test_func._unified_command

        assert metadata["name"] == "test"
        assert metadata["description"] == "Test command"
        assert metadata["permission_node"] is None
        assert metadata["slash_only"] is False
        assert metadata["prefix_only"] is False
        assert metadata["arguments"] == []
        assert metadata["lightbulb_kwargs"] == {}

    def test_command_with_all_parameters(self):
        """Test creating a command with all parameters specified."""
        test_args = [
            CommandArgument("arg1", hikari.OptionType.STRING, "First arg"),
            CommandArgument("arg2", hikari.OptionType.INTEGER, "Second arg"),
        ]

        @command(
            name="fulltest",
            description="Full test command",
            aliases=["ft", "full"],
            permission_node="test.full",
            slash_only=True,
            prefix_only=False,
            arguments=test_args,
            custom_kwarg="custom_value",
        )
        async def full_test_func():
            return "full success"

        # Check unified command metadata
        assert hasattr(full_test_func, "_unified_command")
        metadata = full_test_func._unified_command

        assert metadata["name"] == "fulltest"
        assert metadata["description"] == "Full test command"
        assert metadata["permission_node"] == "test.full"
        assert metadata["slash_only"] is True
        assert metadata["prefix_only"] is False
        assert metadata["arguments"] == test_args
        assert metadata["lightbulb_kwargs"] == {"custom_kwarg": "custom_value"}

    def test_prefix_command_creation_when_not_slash_only(self):
        """Test that prefix command metadata is created when not slash_only."""
        test_args = [CommandArgument("arg1", hikari.OptionType.STRING, "Test arg")]

        @command(
            name="prefixtest",
            description="Prefix test command",
            aliases=["pt", "prefix"],
            permission_node="test.prefix",
            arguments=test_args,
        )
        async def prefix_test_func():
            return "prefix success"

        # Check that prefix command metadata was created
        assert hasattr(prefix_test_func, "_prefix_command")
        prefix_metadata = prefix_test_func._prefix_command

        assert prefix_metadata["name"] == "prefixtest"
        assert prefix_metadata["description"] == "Prefix test command"
        assert prefix_metadata["aliases"] == ["pt", "prefix"]
        assert prefix_metadata["permission_node"] == "test.prefix"
        assert prefix_metadata["arguments"] == test_args

    def test_no_prefix_command_when_slash_only(self):
        """Test that prefix command metadata is not created when slash_only=True."""

        @command(name="slashonly", description="Slash only command", slash_only=True)
        async def slash_only_func():
            return "slash only"

        # Should not have prefix command metadata
        assert not hasattr(slash_only_func, "_prefix_command")

        # But should still have unified command metadata
        assert hasattr(slash_only_func, "_unified_command")

    def test_prefix_command_with_no_aliases(self):
        """Test prefix command creation when no aliases provided."""

        @command(name="noaliases", description="No aliases command")
        async def no_aliases_func():
            return "no aliases"

        assert hasattr(no_aliases_func, "_prefix_command")
        prefix_metadata = no_aliases_func._prefix_command
        assert prefix_metadata["aliases"] == []

    def test_command_with_empty_arguments_list(self):
        """Test command creation with explicitly empty arguments list."""

        @command(name="noargs", description="No args command", arguments=[])
        async def no_args_func():
            return "no args"

        metadata = no_args_func._unified_command
        assert metadata["arguments"] == []

        prefix_metadata = no_args_func._prefix_command
        assert prefix_metadata["arguments"] == []

    def test_command_preserves_function_properties(self):
        """Test that decorator preserves original function properties."""

        @command(name="preserve", description="Preserve test")
        async def original_func():
            """Original docstring"""
            return "original"

        # Function should still be callable
        assert callable(original_func)

        # Function properties should be preserved
        assert original_func.__name__ == "original_func"
        assert original_func.__doc__ == "Original docstring"

    def test_command_with_prefix_only_flag(self):
        """Test command creation with prefix_only=True."""

        @command(name="prefixonly", description="Prefix only command", prefix_only=True)
        async def prefix_only_func():
            return "prefix only"

        metadata = prefix_only_func._unified_command
        assert metadata["prefix_only"] is True
        assert metadata["slash_only"] is False

        # Should still create prefix command metadata
        assert hasattr(prefix_only_func, "_prefix_command")

    def test_command_with_complex_arguments(self):
        """Test command with various argument types."""
        complex_args = [
            CommandArgument(
                "text", hikari.OptionType.STRING, "Text input", required=True
            ),
            CommandArgument(
                "number",
                hikari.OptionType.INTEGER,
                "Number input",
                required=False,
                default=0,
            ),
            CommandArgument("user", hikari.OptionType.USER, "User mention"),
            CommandArgument("channel", hikari.OptionType.CHANNEL, "Channel mention"),
            CommandArgument("role", hikari.OptionType.ROLE, "Role mention"),
        ]

        @command(
            name="complex",
            description="Complex command with various args",
            arguments=complex_args,
        )
        async def complex_func():
            return "complex"

        metadata = complex_func._unified_command
        assert len(metadata["arguments"]) == 5
        assert metadata["arguments"] == complex_args

        prefix_metadata = complex_func._prefix_command
        assert len(prefix_metadata["arguments"]) == 5
        assert prefix_metadata["arguments"] == complex_args

    def test_command_with_lightbulb_kwargs(self):
        """Test command with additional lightbulb-specific keyword arguments."""

        @command(
            name="lightbulb",
            description="Lightbulb specific command",
            guild_only=True,
            owner_only=False,
            hidden=True,
            cooldown_length=60,
            max_concurrency=3,
        )
        async def lightbulb_func():
            return "lightbulb"

        metadata = lightbulb_func._unified_command
        expected_kwargs = {
            "guild_only": True,
            "owner_only": False,
            "hidden": True,
            "cooldown_length": 60,
            "max_concurrency": 3,
        }
        assert metadata["lightbulb_kwargs"] == expected_kwargs

    def test_multiple_commands_independent(self):
        """Test that multiple decorated functions have independent metadata."""

        @command(
            name="first", description="First command", permission_node="first.perm"
        )
        async def first_func():
            return "first"

        @command(name="second", description="Second command", slash_only=True)
        async def second_func():
            return "second"

        # Check that each function has its own independent metadata
        first_meta = first_func._unified_command
        second_meta = second_func._unified_command

        assert first_meta["name"] == "first"
        assert second_meta["name"] == "second"
        assert first_meta["permission_node"] == "first.perm"
        assert second_meta["permission_node"] is None
        assert first_meta["slash_only"] is False
        assert second_meta["slash_only"] is True

        # First should have prefix command, second should not
        assert hasattr(first_func, "_prefix_command")
        assert not hasattr(second_func, "_prefix_command")

    def test_command_decorator_returns_function(self):
        """Test that the decorator returns the original function."""
        original_func = lambda: "test"

        decorated_func = command(name="test", description="Test")(original_func)

        # Should return the same function object (just with added metadata)
        assert decorated_func is original_func

    def test_command_with_none_arguments(self):
        """Test command creation when arguments parameter is None."""

        @command(name="noneargs", description="None args command", arguments=None)
        async def none_args_func():
            return "none args"

        # None should be converted to empty list
        metadata = none_args_func._unified_command
        assert metadata["arguments"] == []

        prefix_metadata = none_args_func._prefix_command
        assert prefix_metadata["arguments"] == []

    def test_command_metadata_immutability(self):
        """Test that modifying one command's metadata doesn't affect others."""

        @command(name="mutable1", description="Mutable test 1")
        async def mutable1_func():
            return "mutable1"

        @command(name="mutable2", description="Mutable test 2")
        async def mutable2_func():
            return "mutable2"

        # Modify first command's metadata
        mutable1_func._unified_command["name"] = "modified"

        # Second command should be unaffected
        assert mutable2_func._unified_command["name"] == "mutable2"

    def test_command_with_both_slash_and_prefix_only_false(self):
        """Test explicit setting of both flags to False."""

        @command(
            name="neither",
            description="Neither exclusive command",
            slash_only=False,
            prefix_only=False,
        )
        async def neither_func():
            return "neither"

        metadata = neither_func._unified_command
        assert metadata["slash_only"] is False
        assert metadata["prefix_only"] is False

        # Should create prefix command metadata
        assert hasattr(neither_func, "_prefix_command")

    def test_command_function_execution_unchanged(self):
        """Test that decorated function can still be executed normally."""

        @command(name="executable", description="Executable test")
        async def executable_func(param="default"):
            return f"executed with {param}"

        # Function should still be executable with same behavior
        import asyncio

        result = asyncio.run(executable_func("test"))
        assert result == "executed with test"

        # And still have metadata
        assert hasattr(executable_func, "_unified_command")
        assert executable_func._unified_command["name"] == "executable"
