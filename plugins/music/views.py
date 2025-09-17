import hikari
import miru
import random


class MusicControlView(miru.View):
    def __init__(self, music_plugin, guild_id: int, *, timeout: float = 300) -> None:
        super().__init__(timeout=timeout)
        self.music_plugin = music_plugin
        self.guild_id = guild_id

    @miru.button(emoji="⏯️", style=hikari.ButtonStyle.SECONDARY)
    async def pause_resume_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        player = self.music_plugin.lavalink_client.player_manager.get(self.guild_id)

        if not player or not player.current:
            await ctx.respond("Nothing is currently playing.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        if player.paused:
            await player.set_pause(False)
            await ctx.respond("▶️ Resumed", flags=hikari.MessageFlag.EPHEMERAL)
        else:
            await player.set_pause(True)
            await ctx.respond("⏸️ Paused", flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(emoji="⏭️", style=hikari.ButtonStyle.SECONDARY)
    async def skip_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        player = self.music_plugin.lavalink_client.player_manager.get(self.guild_id)

        if not player or not player.is_playing:
            await ctx.respond("Nothing is currently playing.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        await player.skip()
        await ctx.respond("⏭️ Skipped", flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(emoji="⏹️", style=hikari.ButtonStyle.DANGER)
    async def stop_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        player = self.music_plugin.lavalink_client.player_manager.get(self.guild_id)

        if not player:
            await ctx.respond("No player found.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player.queue.clear()
        await player.stop()
        await self.music_plugin.bot.hikari_bot.update_voice_state(self.guild_id, None)
        await ctx.respond("⏹️ Stopped and disconnected", flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(emoji="🔀", style=hikari.ButtonStyle.SECONDARY)
    async def shuffle_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        player = self.music_plugin.lavalink_client.player_manager.get(self.guild_id)

        if not player or len(player.queue) < 2:
            await ctx.respond("Need at least 2 tracks in queue to shuffle.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        queue_list = list(player.queue)
        random.shuffle(queue_list)
        player.queue.clear()
        for track in queue_list:
            player.queue.append(track)

        await ctx.respond(f"🔀 Shuffled {len(queue_list)} tracks", flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(emoji="🔁", style=hikari.ButtonStyle.SECONDARY)
    async def loop_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        current_mode = self.music_plugin.repeat_modes.get(self.guild_id, 0)
        new_mode = (current_mode + 1) % 3
        self.music_plugin.repeat_modes[self.guild_id] = new_mode

        if new_mode == 0:
            await ctx.respond("🔁 Loop disabled", flags=hikari.MessageFlag.EPHEMERAL)
        elif new_mode == 1:
            await ctx.respond("🔂 Track repeat enabled", flags=hikari.MessageFlag.EPHEMERAL)
        else:
            await ctx.respond("🔁 Queue repeat enabled", flags=hikari.MessageFlag.EPHEMERAL)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

        if hasattr(self, 'message') and self.message:
            try:
                await self.message.edit(components=self)
            except:
                pass


class SearchResultView(miru.View):
    def __init__(self, music_plugin, guild_id: int, tracks: list, user_id: int, *, timeout: float = 60) -> None:
        super().__init__(timeout=timeout)
        self.music_plugin = music_plugin
        self.guild_id = guild_id
        self.tracks = tracks
        self.user_id = user_id
        self._setup_select_menu()

    def _setup_select_menu(self) -> None:
        if not self.tracks:
            return

        options = []
        for i, track in enumerate(self.tracks[:5]):
            duration_minutes = track.duration // 60000
            duration_seconds = (track.duration % 60000) // 1000
            duration_str = f"{duration_minutes}:{duration_seconds:02d}"

            title = track.title[:80] + "..." if len(track.title) > 80 else track.title
            description = f"By: {track.author} | Duration: {duration_str}"

            options.append(
                miru.SelectOption(
                    label=f"{i + 1}. {title}",
                    value=str(i),
                    description=description[:100],
                    emoji="🎵"
                )
            )

        if options:
            select = miru.TextSelect(
                placeholder="Choose a track to play...",
                options=options,
                custom_id="track_select",
            )
            select.callback = self.on_track_select
            self.add_item(select)

    async def on_track_select(self, ctx: miru.ViewContext) -> None:
        if ctx.user.id != self.user_id:
            await ctx.respond("Only the person who started the search can select a track.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        select = None
        for item in self.children:
            if isinstance(item, miru.TextSelect) and item.custom_id == "track_select":
                select = item
                break

        if not select or not select.values:
            return

        try:
            selected_index = int(select.values[0])
            if selected_index < 0 or selected_index >= len(self.tracks):
                await ctx.respond("Invalid selection.", flags=hikari.MessageFlag.EPHEMERAL)
                return

            selected_track = self.tracks[selected_index]

            voice_state = self.music_plugin.bot.hikari_bot.cache.get_voice_state(self.guild_id, self.user_id)
            if not voice_state or not voice_state.channel_id:
                await ctx.respond("You must be in a voice channel to play music.", flags=hikari.MessageFlag.EPHEMERAL)
                return

            player = self.music_plugin.lavalink_client.player_manager.create(self.guild_id)

            if not player.is_connected:
                await self.music_plugin.bot.hikari_bot.update_voice_state(self.guild_id, voice_state.channel_id)

            player.add(requester=self.user_id, track=selected_track)

            was_playing = player.is_playing
            if not was_playing:
                await player.play()

            duration_minutes = selected_track.duration // 60000
            duration_seconds = (selected_track.duration % 60000) // 1000

            if was_playing:
                queue_position = len(player.queue)
                embed = self.music_plugin.create_embed(
                    title="🎵 Added to Queue",
                    color=hikari.Color(0x00FF00)
                )

                embed.add_field(
                    name="🎶 Track",
                    value=f"**[{selected_track.title}]({selected_track.uri})**\nBy: {selected_track.author}",
                    inline=False
                )

                embed.add_field(
                    name="📍 Position",
                    value=f"#{queue_position} in queue",
                    inline=True
                )

                embed.add_field(
                    name="⏱️ Duration",
                    value=f"`{duration_minutes}:{duration_seconds:02d}`",
                    inline=True
                )
            else:
                embed = self.music_plugin.create_embed(
                    title="🎵 Now Playing",
                    color=hikari.Color(0x00FF00)
                )

                embed.add_field(
                    name="🎶 Track",
                    value=f"**[{selected_track.title}]({selected_track.uri})**\nBy: {selected_track.author}",
                    inline=False
                )

                embed.add_field(
                    name="⏱️ Duration",
                    value=f"`{duration_minutes}:{duration_seconds:02d}`",
                    inline=True
                )

            for item in self.children:
                item.disabled = True

            await ctx.edit_response(embed=embed, components=self)

        except Exception as e:
            await ctx.respond(f"Error adding track: {str(e)}", flags=hikari.MessageFlag.EPHEMERAL)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

        if hasattr(self, 'message') and self.message:
            try:
                timeout_embed = self.music_plugin.create_embed(
                    title="⏰ Search Timeout",
                    description="Track selection timed out. Please use `/search` again.",
                    color=hikari.Color(0xFF9800)
                )
                await self.message.edit(embed=timeout_embed, components=self)
            except:
                pass