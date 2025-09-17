import hikari
import lightbulb
from bot.plugins.commands import CommandArgument, command


def setup_settings_commands(plugin):
    """Setup settings-related commands on the plugin."""

    @command(
        name="music-settings",
        description="Configure music plugin settings",
        aliases=["msettings"],
        permission_node="music.settings",
        arguments=[
            CommandArgument("setting", hikari.OptionType.STRING, "Setting to configure: auto_disconnect_timer", required=False),
            CommandArgument("value", hikari.OptionType.INTEGER, "Value for the setting (1-30 minutes for timer)", required=False)
        ],
    )
    async def music_settings(ctx: lightbulb.Context, setting: str = None, value: int = None) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        if not setting:
            auto_disconnect_minutes = await plugin.get_setting(ctx.guild_id, "auto_disconnect_timer", 5)

            embed = plugin.create_embed(
                title="⚙️ Music Settings",
                description="Current configuration for this server",
                color=hikari.Color(0x0099FF)
            )

            embed.add_field(
                name="🔌 Auto-Disconnect Timer",
                value=f"{auto_disconnect_minutes} minutes\n*Time before bot leaves empty voice channels*",
                inline=False
            )

            embed.add_field(
                name="📝 How to Configure",
                value="Use `/music-settings auto_disconnect_timer <1-30>` to change the timer",
                inline=False
            )

            await plugin.smart_respond(ctx, embed=embed)
            return

        if setting.lower() == "auto_disconnect_timer":
            if value is None:
                await plugin.smart_respond(ctx, "Please provide a value (1-30 minutes) for the auto-disconnect timer.", ephemeral=True)
                return

            if value < 1 or value > 30:
                await plugin.smart_respond(ctx, "Auto-disconnect timer must be between 1 and 30 minutes.", ephemeral=True)
                return

            await plugin.set_setting(ctx.guild_id, "auto_disconnect_timer", value)

            embed = plugin.create_embed(
                title="✅ Setting Updated",
                description=f"Auto-disconnect timer set to **{value} minutes**",
                color=hikari.Color(0x00FF00)
            )

            embed.add_field(
                name="ℹ️ Effect",
                value=f"Bot will now leave voice channels after {value} minutes of inactivity",
                inline=False
            )

            await plugin.smart_respond(ctx, embed=embed)
        else:
            await plugin.smart_respond(ctx, "Unknown setting. Available settings: `auto_disconnect_timer`", ephemeral=True)

    return [music_settings]