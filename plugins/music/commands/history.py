import logging

import hikari
import lightbulb

from bot.plugins.commands import CommandArgument, command

logger = logging.getLogger(__name__)


def setup_history_commands(plugin):
    """Setup history-related commands on the plugin."""

    @command(
        name="history",
        description="Show recently played tracks",
        aliases=["recent"],
        permission_node="music.play",
        arguments=[
            CommandArgument("page", hikari.OptionType.INTEGER, "Page number (shows 5 tracks per page)", required=False, default=1)
        ],
    )
    async def music_history(ctx: lightbulb.Context, page: int = 1) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        try:
            async with plugin.bot.db.session() as session:
                from sqlalchemy import select

                from bot.database.models import MusicQueue

                result = await session.execute(
                    select(MusicQueue)
                    .where(MusicQueue.guild_id == ctx.guild_id, MusicQueue.position == -1)
                    .order_by(MusicQueue.created_at.desc())
                )
                history_tracks = result.scalars().all()

                if not history_tracks:
                    embed = plugin.create_embed(
                        title="📜 Music History", description="No recently played tracks found.", color=hikari.Color(0x888888)
                    )
                    embed.add_field(name="💡 Tip", value="Play some music to start building your history!", inline=False)
                    await plugin.smart_respond(ctx, embed=embed)
                    return

                tracks_per_page = 5
                total_tracks = len(history_tracks)
                max_pages = max(1, (total_tracks + tracks_per_page - 1) // tracks_per_page)

                if page < 1 or page > max_pages:
                    await plugin.smart_respond(ctx, f"Invalid page. Please use a page between 1 and {max_pages}.", ephemeral=True)
                    return

                start_idx = (page - 1) * tracks_per_page
                end_idx = min(start_idx + tracks_per_page, total_tracks)
                page_tracks = history_tracks[start_idx:end_idx]

                embed = plugin.create_embed(
                    title="📜 Music History", description="Recently played tracks in this server", color=hikari.Color(0x9932CC)
                )

                history_text = ""
                for i, track in enumerate(page_tracks, start=start_idx + 1):
                    duration_minutes = track.track_duration // 60000
                    duration_seconds = (track.track_duration % 60000) // 1000

                    try:
                        user = await ctx.bot.hikari_bot.rest.fetch_user(track.requester_id)
                        requester_name = user.display_name or user.username
                    except (hikari.NotFoundError, hikari.ForbiddenError, hikari.HTTPError):
                        requester_name = "Unknown"

                    timestamp = f"<t:{int(track.created_at.timestamp())}:R>"

                    history_text += f"`{i}.` **[{track.track_title}]({track.track_uri})**\n"
                    history_text += f"    └ By: {track.track_author} | Duration: `{duration_minutes}:{duration_seconds:02d}`\n"
                    history_text += f"    └ Played {timestamp} • Requested by: {requester_name}\n\n"

                embed.add_field(name=f"🎵 Recently Played (Page {page}/{max_pages})", value=history_text, inline=False)

                embed.add_field(name="📊 Statistics", value=f"Total tracks in history: **{total_tracks}**", inline=True)

                if max_pages > 1:
                    embed.set_footer(text=f"Page {page} of {max_pages} • Use /history <page> to view other pages")

                await plugin.smart_respond(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error retrieving music history for guild {ctx.guild_id}: {e}")
            embed = plugin.create_embed(
                title="❌ History Error",
                description="Failed to retrieve music history. Please try again.",
                color=hikari.Color(0xFF0000),
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)

    return [music_history]
