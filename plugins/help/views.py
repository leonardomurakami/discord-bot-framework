import logging
import hikari
import miru

logger = logging.getLogger(__name__)


class PersistentPluginSelectView(miru.View):
    """Persistent view for plugin selection that survives bot restarts."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(timeout=None, *args, **kwargs)
        self._setup_select_menu()

    def _setup_select_menu(self) -> None:
        """Setup a placeholder select menu - will be updated when used."""
        # This is just a placeholder that will be replaced when the view is actually used
        select = miru.TextSelect(
            placeholder="Loading plugins...",
            options=[miru.SelectOption(label="Loading...", value="loading")],
            custom_id="help_plugin_select",
        )
        select.callback = self.on_plugin_select
        self.add_item(select)

    async def on_plugin_select(self, ctx: miru.ViewContext) -> None:
        """Handle plugin selection - this will be called even after bot restart."""
        try:
            # Find the help plugin instance through multiple approaches
            help_plugin_instance = None

            # Method 1: Try through the global bot instance reference (most reliable)
            try:
                # Import here to avoid circular imports
                from bot.permissions.decorators import _bot_instance

                if _bot_instance and hasattr(_bot_instance, "plugin_loader"):
                    help_plugin_instance = _bot_instance.plugin_loader.plugins.get("help")
            except (ImportError, AttributeError):
                pass

            # Method 2: Try through miru client's app reference
            if not help_plugin_instance and hasattr(ctx.client, "app"):
                bot_app = ctx.client.app
                if hasattr(bot_app, "plugin_loader") and hasattr(bot_app.plugin_loader, "plugins"):
                    help_plugin_instance = bot_app.plugin_loader.plugins.get("help")

            # Method 3: Try through context bot reference
            if not help_plugin_instance and hasattr(ctx, "bot"):
                bot_instance = ctx.bot
                if hasattr(bot_instance, "plugin_loader") and hasattr(bot_instance.plugin_loader, "plugins"):
                    help_plugin_instance = bot_instance.plugin_loader.plugins.get("help")

            # Debug logging
            logger.debug("Looking for help plugin instance...")
            logger.debug(f"Found help plugin: {help_plugin_instance}")

            if not help_plugin_instance:
                await ctx.respond(
                    "Help system temporarily unavailable. Please try using the help command again.",
                    flags=hikari.MessageFlag.EPHEMERAL,
                )
                return

            # Handle the selection using the help plugin
            select = None
            for item in self.children:
                if isinstance(item, miru.TextSelect) and item.custom_id == "help_plugin_select":
                    select = item
                    break

            if not select or not select.values:
                return

            selected_value = select.values[0]

            if selected_value == "loading":
                await ctx.respond(
                    "Please wait for the help system to fully load.",
                    flags=hikari.MessageFlag.EPHEMERAL,
                )
                return

            # Handle "Home" selection
            if selected_value == "__home__":
                from .embed_generators import EmbedGenerators
                embed_gen = EmbedGenerators(help_plugin_instance)
                home_embed = await embed_gen.get_general_help()
                # Update the view with current plugin options
                new_view = PluginSelectView(help_plugin_instance)
                await ctx.edit_response(embed=home_embed, components=new_view)
                return

            # Generate plugin-specific embed
            from .embed_generators import EmbedGenerators
            embed_gen = EmbedGenerators(help_plugin_instance)
            plugin_embed = await embed_gen.get_plugin_commands_embed(selected_value)

            if plugin_embed:
                # Update the view with current plugin options
                new_view = PluginSelectView(help_plugin_instance)
                await ctx.edit_response(embed=plugin_embed, components=new_view)
            else:
                error_embed = help_plugin_instance.create_embed(
                    title="❌ Plugin Not Found",
                    description=f"Could not find information for plugin: {selected_value}",
                    color=hikari.Color(0xFF0000),
                )
                new_view = PluginSelectView(help_plugin_instance)
                await ctx.edit_response(embed=error_embed, components=new_view)

        except Exception as e:
            logger.error(f"Error in persistent view callback: {e}")
            await ctx.respond(
                "An error occurred while processing your request.",
                flags=hikari.MessageFlag.EPHEMERAL,
            )


class PluginSelectView(miru.View):
    def __init__(self, help_plugin: "HelpPlugin", *args, **kwargs) -> None:
        # Make the view persistent by setting timeout=None
        super().__init__(timeout=None, *args, **kwargs)
        self.help_plugin = help_plugin
        self._setup_select_menu()

    def _setup_select_menu(self) -> None:
        """Setup the plugin selection dropdown menu."""
        try:
            plugins = self.help_plugin.bot.plugin_loader.get_loaded_plugins()
        except (AttributeError, TypeError):
            # Handle case where plugin_loader is None or doesn't have get_loaded_plugins
            return

        if not plugins:
            return

        options = [
            # Add "Home" option first
            miru.SelectOption(
                label="🏠 General Help",
                value="__home__",
                description="Return to the main help overview",
                emoji="🏠",
            )
        ]

        for plugin_name in sorted(plugins):
            try:
                plugin_info = self.help_plugin.bot.plugin_loader.get_plugin_info(plugin_name)
                if plugin_info:
                    description = plugin_info.description[:100] if plugin_info.description else "No description"
                    options.append(
                        miru.SelectOption(
                            label=plugin_info.name,
                            value=plugin_name,
                            description=description,
                            emoji="🔌",
                        )
                    )
            except (AttributeError, TypeError):
                # Handle case where plugin_info is None or invalid
                continue

        if len(options) > 1:  # Only add if we have actual plugins plus home
            select = miru.TextSelect(
                placeholder="Select a plugin to view commands or return home...",
                options=options[:25],  # Discord limit
                custom_id="help_plugin_select",  # Unique custom_id for persistence
            )
            select.callback = self.on_plugin_select
            self.add_item(select)

    async def on_plugin_select(self, ctx: miru.ViewContext) -> None:
        """Handle plugin selection from dropdown - update the original embed."""
        # Get the select component that triggered this callback
        select = None
        for item in self.children:
            if isinstance(item, miru.TextSelect) and item.custom_id == "help_plugin_select":
                select = item
                break

        if not select or not select.values:
            return

        selected_value = select.values[0]

        from .embed_generators import EmbedGenerators
        embed_gen = EmbedGenerators(self.help_plugin)

        # Handle "Home" selection
        if selected_value == "__home__":
            home_embed = await embed_gen.get_general_help()
            await ctx.edit_response(embed=home_embed, components=self)
            return

        # Generate plugin-specific embed with commands
        plugin_embed = await embed_gen.get_plugin_commands_embed(selected_value)

        if plugin_embed:
            # Update the original message with the new embed, keeping the dropdown
            await ctx.edit_response(embed=plugin_embed, components=self)
        else:
            # Show error but keep the dropdown
            error_embed = self.help_plugin.create_embed(
                title="❌ Plugin Not Found",
                description=f"Could not find information for plugin: {selected_value}",
                color=hikari.Color(0xFF0000),
            )
            await ctx.edit_response(embed=error_embed, components=self)