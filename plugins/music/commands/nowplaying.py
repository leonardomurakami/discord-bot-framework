import hikari
import lightbulb
from bot.plugins.commands import command
from ..views import MusicControlView


def setup_nowplaying_commands(plugin):
    """Setup now playing related commands on the plugin."""

    @command(
        name="nowplaying",
        description="Show the currently playing track with detailed information",
        aliases=["np", "current"],
        permission_node="music.play",
    )
    async def now_playing(ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = plugin.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or not player.current:
            await plugin.smart_respond(ctx, "Nothing is currently playing.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        track = player.current
        current_pos = player.position
        duration = track.duration

        current_minutes = current_pos // 60000
        current_seconds = (current_pos % 60000) // 1000
        duration_minutes = duration // 60000
        duration_seconds = (duration % 60000) // 1000

        progress_percentage = current_pos / duration if duration > 0 else 0
        bar_length = 25
        filled_length = int(bar_length * progress_percentage)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)

        requester = track.requester
        try:
            user = await ctx.bot.rest.fetch_user(requester)
            requester_mention = user.mention
        except:
            requester_mention = f"<@{requester}>"

        status_emoji = "⏸️" if player.paused else "▶️"

        embed = plugin.create_embed(
            title=f"{status_emoji} Now Playing",
            color=hikari.Color(0x00FF00) if not player.paused else hikari.Color(0xFFFF00)
        )

        embed.add_field(
            name="🎵 Track",
            value=f"**[{track.title}]({track.uri})**\nBy: {track.author}",
            inline=False
        )

        embed.add_field(
            name="⏱️ Progress",
            value=f"`{current_minutes}:{current_seconds:02d}` {bar} `{duration_minutes}:{duration_seconds:02d}`\n"
                  f"{progress_percentage:.1%} complete",
            inline=False
        )

        status_info = []
        status_info.append(f"🔊 Volume: {player.volume}%")

        repeat_mode = plugin.repeat_modes.get(ctx.guild_id, 0)
        if repeat_mode == 1:
            status_info.append("🔂 Repeat: Track")
        elif repeat_mode == 2:
            status_info.append("🔁 Repeat: Queue")

        if len(player.queue) > 0:
            status_info.append(f"📋 Queue: {len(player.queue)} tracks")

        embed.add_field(
            name="ℹ️ Status",
            value="\n".join(status_info),
            inline=True
        )

        embed.add_field(
            name="👤 Requested by",
            value=requester_mention,
            inline=True
        )

        if hasattr(track, 'artwork_url') and track.artwork_url:
            embed.set_thumbnail(track.artwork_url)

        view = MusicControlView(plugin, ctx.guild_id)

        miru_client = getattr(plugin.bot, "miru_client", None)
        if miru_client and view.children:
            message = await ctx.respond(embed=embed, components=view)
            miru_client.start_view(view)

            if hasattr(message, 'message'):
                view.message = message.message
            elif hasattr(message, 'id'):
                view.message = message
        else:
            await ctx.respond(embed=embed)

    return [now_playing]