import logging

import hikari
import lightbulb

from bot.plugins.base import BasePlugin
from bot.plugins.commands import CommandArgument, command

from .views.embed_generators import EmbedGenerators
from .views import PersistentPluginSelectView, PluginSelectWithPaginationView

logger = logging.getLogger(__name__)


class HelpPlugin(BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)
        self._persistent_view_registered = False

    async def on_load(self) -> None:
        """Register persistent views on plugin load."""
        await super().on_load()
        await self._register_persistent_views()

    async def _register_persistent_views(self) -> None:
        """Register persistent help views with miru client."""
        if self._persistent_view_registered:
            return

        miru_client = getattr(self.bot, "miru_client", None)
        if miru_client:
            # Create and register the persistent view
            persistent_view = PersistentPluginSelectView()
            miru_client.start_view(persistent_view, bind_to=None)
            self._persistent_view_registered = True
            self.logger.info("Registered persistent help view")

    # Delegation methods for tests (these delegate to EmbedGenerators)
    async def _get_general_help(self, guild_id: int = None):
        """Test delegation method."""
        embed_gen = EmbedGenerators(self)
        return await embed_gen.get_general_help(guild_id)

    async def _get_command_help(self, command_name: str, guild_id: int = None):
        """Test delegation method."""
        embed_gen = EmbedGenerators(self)
        return await embed_gen.get_command_help(command_name, guild_id)

    async def _get_plugin_help(self, plugin_name: str):
        """Test delegation method."""
        embed_gen = EmbedGenerators(self)
        return await embed_gen.get_plugin_help(plugin_name)

    async def _get_commands_list(self):
        """Test delegation method."""
        embed_gen = EmbedGenerators(self)
        return await embed_gen.get_commands_list()

    async def _get_plugins_list(self):
        """Test delegation method."""
        embed_gen = EmbedGenerators(self)
        return await embed_gen.get_plugins_list()

    async def _get_plugin_commands_embed(self, plugin_name: str, guild_id: int = None, page: int = 0):
        """Test delegation method."""
        embed_gen = EmbedGenerators(self)
        result = await embed_gen.get_plugin_commands_embed(plugin_name, guild_id, page)
        # The method returns (embed, metadata) but tests expect just embed
        if isinstance(result, tuple):
            return result[0]
        return result

    async def _get_command_info(self, command_name: str):
        """Test delegation method."""
        from .models.command_info import CommandInfoManager

        info_manager = CommandInfoManager(self)
        return info_manager.get_command_info(command_name)

    def _get_plugin_overview(self, plugin_name: str, plugin_obj):
        """Test delegation method."""
        from .models.command_info import CommandInfoManager

        info_manager = CommandInfoManager(self)
        return info_manager.get_plugin_overview(plugin_name, plugin_obj)

    def _format_command_list(self, commands: list[dict]):
        """Test delegation method."""
        from .models.command_info import CommandInfoManager

        info_manager = CommandInfoManager(self)
        return info_manager.format_command_list(commands)

    @command(
        name="help",
        description="Show help information for commands and plugins",
        aliases=["h"],
        arguments=[
            CommandArgument(
                "query",
                hikari.OptionType.STRING,
                "Command name, plugin name, or category to get help for",
                required=False,
            )
        ],
    )
    async def help_command(self, ctx: lightbulb.Context, query: str = None) -> None:
        """Main help command that provides comprehensive help information."""
        try:
            embed_gen = EmbedGenerators(self)

            if query:
                # Show specific help for command or plugin
                query = query.lower().strip()

                # First, try to find a specific command
                command_help = await embed_gen.get_command_help(query, ctx.guild_id)
                if command_help:
                    await ctx.respond(embed=command_help)
                    await self.log_command_usage(ctx, "help", True)
                    return

                # Then try to find a plugin
                plugin_help = await embed_gen.get_plugin_help(query)
                if plugin_help:
                    await ctx.respond(embed=plugin_help)
                    await self.log_command_usage(ctx, "help", True)
                    return

                # Nothing found
                embed = self.create_embed(
                    title="❌ Help Not Found",
                    description=f"No help found for `{query}`. Use `help` without arguments to see all available commands.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
            else:
                # Show general help with plugin dropdown and pagination
                help_embed = await embed_gen.get_general_help(ctx.guild_id)
                view = PluginSelectWithPaginationView(self)

                # Check if miru client is available
                miru_client = getattr(self.bot, "miru_client", None)
                if miru_client and view.children:
                    await ctx.respond(embed=help_embed, components=view)
                    miru_client.start_view(view)
                else:
                    await ctx.respond(embed=help_embed)

            await self.log_command_usage(ctx, "help", True)

        except Exception as e:
            logger.error(f"Error in help command: {e}")
            embed = self.create_embed(
                title="❌ Help Error",
                description="Failed to retrieve help information. Please try again later.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "help", False, str(e))

    @command(
        name="commands",
        description="List all available commands organized by plugin",
        aliases=["cmds"],
        permission_node="basic.commands",
    )
    async def list_commands(self, ctx: lightbulb.Context) -> None:
        """List all available commands organized by plugin."""
        try:
            embed_gen = EmbedGenerators(self)
            embed = await embed_gen.get_commands_list()
            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "commands", True)

        except Exception as e:
            logger.error(f"Error in commands command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to retrieve commands list.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "commands", False, str(e))

    @command(
        name="plugins",
        description="List all loaded plugins with their information",
        aliases=["plugin-list"],
        permission_node="basic.plugins",
    )
    async def list_plugins(self, ctx: lightbulb.Context) -> None:
        """List all loaded plugins with their information."""
        try:
            embed_gen = EmbedGenerators(self)
            embed = await embed_gen.get_plugins_list()
            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "plugins", True)

        except Exception as e:
            logger.error(f"Error in plugins command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to retrieve plugins list.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "plugins", False, str(e))
