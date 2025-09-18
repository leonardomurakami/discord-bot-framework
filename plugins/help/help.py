import logging

import hikari
import lightbulb
import miru

from bot.plugins.base import BasePlugin
from bot.plugins.commands import CommandArgument, command
from .views import PersistentPluginSelectView, PluginSelectView
from .embed_generators import EmbedGenerators

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
                command_help = await embed_gen.get_command_help(query)
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
                # Show general help with plugin dropdown
                help_embed = await embed_gen.get_general_help()
                view = PluginSelectView(self)

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
        permission_node="help.commands",
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
        permission_node="help.plugins",
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

