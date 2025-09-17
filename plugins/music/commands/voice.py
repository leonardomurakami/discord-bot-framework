import hikari
import lightbulb

from bot.plugins.commands import CommandArgument, command

from ..utils import cancel_disconnect_timer


def setup_voice_commands(plugin):
    """Setup voice-related commands on the plugin."""

    @command(
        name="join",
        description="Join your voice channel",
        permission_node="music.play",
    )
    async def join_voice(ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        voice_state = ctx.bot.hikari_bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)
        if not voice_state or not voice_state.channel_id:
            await plugin.smart_respond(ctx, "You must be in a voice channel for me to join.", ephemeral=True)
            return

        player = plugin.lavalink_client.player_manager.create(ctx.guild_id)

        if player.is_connected and player.channel_id == voice_state.channel_id:
            await plugin.smart_respond(ctx, "I'm already in your voice channel.", ephemeral=True)
            return

        await ctx.bot.hikari_bot.update_voice_state(ctx.guild_id, voice_state.channel_id)

        try:
            channel = await ctx.bot.rest.fetch_channel(voice_state.channel_id)
            channel_name = channel.name
        except (hikari.NotFoundError, hikari.ForbiddenError, hikari.HTTPError):
            channel_name = "Unknown Channel"

        embed = plugin.create_embed(
            title="🔗 Joined Voice Channel", description=f"Connected to **{channel_name}**", color=hikari.Color(0x00FF00)
        )

        embed.add_field(name="🎵 Ready to Play", value="Use `/play` to start playing music!", inline=False)

        await plugin.smart_respond(ctx, embed=embed)

    @command(
        name="disconnect",
        description="Disconnect from voice channel",
        aliases=["leave"],
        permission_node="music.manage",
    )
    async def disconnect(ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        player = plugin.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or not player.is_connected:
            await plugin.smart_respond(ctx, "I'm not connected to a voice channel.", ephemeral=True)
            return

        await cancel_disconnect_timer(plugin, ctx.guild_id)

        channel_name = "Unknown Channel"
        if player.channel_id:
            try:
                channel = await ctx.bot.rest.fetch_channel(player.channel_id)
                channel_name = channel.name
            except (hikari.NotFoundError, hikari.ForbiddenError, hikari.HTTPError):
                pass

        await player.stop()
        player.queue.clear()
        await ctx.bot.hikari_bot.update_voice_state(ctx.guild_id, None)

        embed = plugin.create_embed(
            title="👋 Disconnected", description=f"Left **{channel_name}** and cleared the queue", color=hikari.Color(0xFF9800)
        )

        await plugin.smart_respond(ctx, embed=embed)

    @command(
        name="volume",
        description="Set or check the volume (0-100)",
        permission_node="music.play",
        arguments=[CommandArgument("level", hikari.OptionType.INTEGER, "Volume level (0-100)", required=False)],
    )
    async def volume(ctx: lightbulb.Context, level: int = None) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = plugin.lavalink_client.player_manager.get(ctx.guild_id)

        if not player:
            await plugin.smart_respond(ctx, "No player found.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        if level is None:
            embed = plugin.create_embed(
                title="🔊 Volume", description=f"Current volume: **{player.volume}%**", color=hikari.Color(0x0099FF)
            )
            await plugin.smart_respond(ctx, embed=embed)
            return

        if level < 0 or level > 100:
            await plugin.smart_respond(ctx, "Volume must be between 0 and 100.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        await player.set_volume(level)

        if level == 0:
            emoji = "🔇"
        elif level <= 30:
            emoji = "🔉"
        elif level <= 70:
            emoji = "🔊"
        else:
            emoji = "📢"

        embed = plugin.create_embed(
            title=f"{emoji} Volume Set", description=f"Volume set to **{level}%**", color=hikari.Color(0x00FF00)
        )
        await plugin.smart_respond(ctx, embed=embed)

    return [join_voice, disconnect, volume]
