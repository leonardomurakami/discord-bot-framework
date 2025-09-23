import logging

import hikari
import lightbulb

from bot.plugins.commands import CommandArgument, command

from ..views import SearchResultView

logger = logging.getLogger(__name__)


def setup_search_commands(plugin):
    """Setup search-related commands on the plugin."""

    @command(
        name="search",
        description="Search for tracks and choose from multiple results",
        permission_node="basic.music.search.use",
        arguments=[CommandArgument("query", hikari.OptionType.STRING, "Song name or artist to search for")],
    )
    async def search_tracks(ctx: lightbulb.Context, query: str) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        voice_state = ctx.bot.hikari_bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)
        if not voice_state or not voice_state.channel_id:
            await plugin.smart_respond(ctx, "You must be in a voice channel to use this command.", ephemeral=True)
            return

        try:
            search_result = await plugin.lavalink_client.get_tracks(f"ytsearch:{query}")

            if not search_result.tracks:
                embed = plugin.create_embed(
                    title="🔍 No Results", description=f"No tracks found for: `{query}`", color=hikari.Color(0xFF6B6B)
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            embed = plugin.create_embed(
                title="🔍 Search Results",
                description=(
                    f"Found {len(search_result.tracks)} results for: **{query}**\n\n"
                    "Select a track from the dropdown below to add it to the queue."
                ),
                color=hikari.Color(0x0099FF),
            )

            tracks_text = ""
            for i, track in enumerate(search_result.tracks[:5]):
                duration_minutes = track.duration // 60000
                duration_seconds = (track.duration % 60000) // 1000
                tracks_text += (
                    f"`{i + 1}.` **{track.title}**\n"
                    f"    └ By: {track.author} | Duration: `{duration_minutes}:{duration_seconds:02d}`\n\n"
                )

            embed.add_field(name="🎵 Tracks Found", value=tracks_text, inline=False)

            embed.add_field(
                name="ℹ️ How to Use",
                value=(
                    "• Use the dropdown menu below to select a track\n"
                    "• Only you can select from your search results\n"
                    "• Selection expires in 60 seconds"
                ),
                inline=False,
            )

            view = SearchResultView(plugin, ctx.guild_id, search_result.tracks, ctx.author.id)

            miru_client = getattr(plugin.bot, "miru_client", None)
            if miru_client and view.children:
                message = await ctx.respond(embed=embed, components=view)
                miru_client.start_view(view)

                if hasattr(message, "message"):
                    view.message = message.message
                elif hasattr(message, "id"):
                    view.message = message
            else:
                first_track = search_result.tracks[0]

                player = plugin.lavalink_client.player_manager.create(ctx.guild_id)

                if not player.is_connected:
                    await ctx.bot.hikari_bot.update_voice_state(ctx.guild_id, voice_state.channel_id)

                player.add(requester=ctx.author.id, track=first_track)

                was_playing = player.is_playing
                if not was_playing:
                    await player.play()

                duration_minutes = first_track.duration // 60000
                duration_seconds = (first_track.duration % 60000) // 1000

                fallback_embed = plugin.create_embed(
                    title="🎵 Added First Result",
                    description=(
                        f"**[{first_track.title}]({first_track.uri})**\n"
                        f"By: {first_track.author}\nDuration: `{duration_minutes}:{duration_seconds:02d}`"
                    ),
                    color=hikari.Color(0x00FF00),
                )

                await plugin.smart_respond(ctx, embed=fallback_embed)

        except Exception as e:
            logger.error(f"Error in search command: {e}")
            embed = plugin.create_embed(
                title="❌ Search Error", description="Failed to search for tracks. Please try again.", color=hikari.Color(0xFF0000)
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)

    return [search_tracks]
