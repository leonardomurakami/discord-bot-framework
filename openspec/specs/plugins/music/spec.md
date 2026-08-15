## Purpose
Provides an advanced music system with Lavalink integration, persistent queue/session storage, interactive controls, search selection UI, auto-disconnect, and web panel management.

## Requirements

### Requirement: Lavalink Integration
The plugin SHALL initialize and manage a Lavalink client for audio playback with voice state forwarding.

#### Scenario: Initialize Lavalink client on plugin load
- **WHEN** the MusicPlugin loads
- **THEN** the plugin SHALL create a Lavalink.Client with the bot's user ID, add a node using lavalink_host, lavalink_port, and lavalink_password from settings, and register MusicEventHandler

#### Scenario: Forward voice events to Lavalink
- **WHEN** a VoiceServerUpdateEvent or VoiceStateUpdateEvent occurs
- **THEN** the plugin SHALL transform and forward the event data to the Lavalink voice_update_handler

#### Scenario: Handle track events
- **WHEN** Lavalink emits TrackStartEvent, TrackEndEvent, TrackExceptionEvent, or QueueEndEvent
- **THEN** the MusicEventHandler SHALL log the event, add tracks to history, handle repeat modes, save queue state, and broadcast updates to WebSocket clients

### Requirement: Playback Control Commands
The plugin SHALL provide commands for controlling music playback with queue management.

#### Scenario: Play a track or playlist
- **WHEN** a user with `basic.music.playback.control` permission invokes `/play <query>` while in a voice channel
- **THEN** the bot SHALL join the voice channel if not connected, search for the track (URL or YouTube Music), add to queue, start playback if not playing, save queue to database, and broadcast update

#### Scenario: Pause and resume playback
- **WHEN** a user invokes `/pause` or `/resume`
- **THEN** the bot SHALL set the player's pause state accordingly and broadcast the playback update

#### Scenario: Stop playback and clear queue
- **WHEN** a user invokes `/stop`
- **THEN** the bot SHALL stop the player, clear the queue, disconnect from voice, clear database queue, and broadcast update

#### Scenario: Skip current track
- **WHEN** a user invokes `/skip`
- **THEN** the bot SHALL handle repeat track mode by re-adding current track, skip to next track, ensure playback continues, save queue, and display next track information

#### Scenario: Seek to position in track
- **WHEN** a user invokes `/seek <position>` with mm:ss or seconds format
- **THEN** the bot SHALL validate the position is within track bounds and seek to that position

#### Scenario: Display current track position
- **WHEN** a user invokes `/position`
- **THEN** the bot SHALL display a progress bar with current position, duration, and percentage complete

### Requirement: Queue Management Commands
The plugin SHALL provide commands for viewing and manipulating the music queue with pagination and persistence.

#### Scenario: Display queue with pagination
- **WHEN** a user with `basic.music.queue.view` permission invokes `/queue [page]`
- **THEN** the bot SHALL display the current track, up to 5 queued tracks per page, total duration, repeat mode, and volume

#### Scenario: Shuffle the queue
- **WHEN** a user with `basic.music.queue.control` permission invokes `/shuffle`
- **THEN** the bot SHALL randomize the queue order (requiring at least 2 tracks), save to database, and broadcast update

#### Scenario: Toggle loop modes
- **WHEN** a user with `basic.music.queue.control` permission invokes `/loop [mode]` with mode off/track/queue
- **THEN** the plugin SHALL set repeat mode (0=off, 1=track, 2=queue) and broadcast the repeat update

#### Scenario: Remove track from queue
- **WHEN** a user with `music.queue.manage` permission invokes `/remove <position>`
- **THEN** the bot SHALL remove the track at the 1-based position, save queue, and broadcast update

#### Scenario: Move track in queue
- **WHEN** a user with `music.queue.manage` permission invokes `/move <from> <to>`
- **THEN** the bot SHALL move the track from one position to another, save queue, and broadcast update

#### Scenario: Clear the queue
- **WHEN** a user with `music.queue.manage` permission invokes `/clear`
- **THEN** the bot SHALL remove all queued tracks (keeping current track), save queue, and broadcast update

### Requirement: Voice Control Commands
The plugin SHALL provide commands for voice channel connection and audio settings.

#### Scenario: Join voice channel
- **WHEN** a user with `basic.music.voice.control` permission invokes `/join`
- **THEN** the bot SHALL connect to the user's voice channel and display ready message

#### Scenario: Disconnect from voice channel
- **WHEN** a user with `music.voice.manage` permission invokes `/disconnect`
- **THEN** the bot SHALL cancel disconnect timer, stop playback, clear queue, leave voice channel, and display confirmation

#### Scenario: Set or check volume
- **WHEN** a user with `basic.music.voice.control` permission invokes `/volume [level]` with level 0-100
- **THEN** the bot SHALL set the player volume or display current volume, and broadcast volume update

### Requirement: Search and Selection UI
The plugin SHALL provide interactive search with dropdown selection using Miru components.

#### Scenario: Search for tracks
- **WHEN** a user with `basic.music.search.use` permission invokes `/search <query>`
- **THEN** the bot SHALL search YouTube Music, display up to 5 results in an embed, and present a dropdown for selection if Miru is available

#### Scenario: Fallback when Miru unavailable
- **WHEN** the search command executes but Miru client is not available
- **THEN** the bot SHALL automatically add the first search result to the queue and display fallback embed

### Requirement: Queue and Session Persistence
The plugin SHALL persist queue and session state to the database for recovery after restarts.

#### Scenario: Save queue to database
- **WHEN** the queue state changes (play, skip, shuffle, etc.)
- **THEN** the plugin SHALL save all queued tracks with position, track metadata, requester ID, and session state (playing, paused, volume, repeat mode, position) to MusicQueue and MusicSession tables

#### Scenario: Restore queue on startup
- **WHEN** the MusicPlugin loads
- **THEN** the plugin SHALL asynchronously restore all guild queues from the database by fetching track URIs and rebuilding the player state

#### Scenario: Add track to history
- **WHEN** a track starts playing
- **THEN** the plugin SHALL add the track to history with position=-1, maintain max 50 entries per guild, and clean old entries

#### Scenario: Clear queue from database
- **WHEN** the player stops or disconnects
- **THEN** the plugin SHALL delete the guild's queue and session records from the database

### Requirement: Auto-Disconnect Feature
The plugin SHALL automatically disconnect from empty voice channels after a configurable timeout.

#### Scenario: Start disconnect timer on empty channel
- **WHEN** the voice channel becomes empty (no non-bot users)
- **THEN** the plugin SHALL start a timer using the guild's auto_disconnect_timer setting (default 5 minutes)

#### Scenario: Cancel disconnect timer on user join
- **WHEN** a non-bot user joins the voice channel
- **THEN** the plugin SHALL cancel any pending disconnect timer

#### Scenario: Execute auto-disconnect
- **WHEN** the disconnect timer expires and channel remains empty
- **THEN** the plugin SHALL stop playback, clear queue, disconnect from voice, and clear the timer

### Requirement: Music Settings Configuration
The plugin SHALL provide per-guild settings for music behavior.

#### Scenario: View music settings
- **WHEN** a user with `music.settings.manage` permission invokes `/music-settings`
- **THEN** the bot SHALL display current settings including auto_disconnect_timer

#### Scenario: Configure auto-disconnect timer
- **WHEN** a user with `music.settings.manage` permission invokes `/music-settings auto_disconnect_timer <value>` with value 1-30
- **THEN** the plugin SHALL update the guild's auto_disconnect_timer setting and display confirmation

### Requirement: Web Panel Integration
The plugin SHALL provide a web panel with WebSocket support for real-time music status and controls.

#### Scenario: Serve music panel interface
- **WHEN** a user accesses `/plugin/music` route
- **THEN** the plugin SHALL render the panel.html template

#### Scenario: Provide music status via REST API
- **WHEN** a client requests `/api/music/status/{guild_id}`
- **THEN** the plugin SHALL return JSON with connected state, current track, queue, volume, repeat mode, and shuffle status

#### Scenario: Handle WebSocket connections
- **WHEN** a client connects to `/ws/music/{guild_id}`
- **THEN** the MusicWebSocketManager SHALL accept the connection, send initial status, and handle ping/pong keepalive

#### Scenario: Broadcast music updates
- **WHEN** music state changes (track start/end, queue update, playback control)
- **THEN** the plugin SHALL broadcast the update to all WebSocket clients for the guild

#### Scenario: Handle web playback controls
- **WHEN** a POST request is made to `/api/music/controls/{action}` with guild_id
- **THEN** the plugin SHALL execute the action (play/pause/stop/skip), update state, save queue, and broadcast update

### Requirement: Music Configuration
The plugin SHALL load configuration for timeouts, limits, and defaults.

#### Scenario: Load music settings
- **WHEN** the MusicPlugin initializes
- **THEN** the plugin SHALL load disconnect_timeout_seconds (default 300), check_empty_interval_seconds (default 5), control_view_timeout_seconds (default 300), queue_view_timeout_seconds (default 300), max_queue_size (default 100), max_search_results (default 10), max_history_entries (default 20), default_volume (default 50), and max_volume (default 100)
