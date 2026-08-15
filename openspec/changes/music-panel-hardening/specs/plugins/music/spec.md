## ADDED Requirements

### Requirement: Web Panel Guild Authorization
The plugin SHALL authorize every music web panel request against the authenticated user's Discord guild membership before acting on a guild, treating the supplied `guild_id` as untrusted input.

#### Scenario: Reject request for a guild the user does not belong to
- **WHEN** an authenticated panel user submits a request (REST or WebSocket) targeting a `guild_id` that is not present in the user's Discord guild list from the session
- **THEN** the plugin SHALL reject the request with a 403 response (or close the WebSocket without acting) and SHALL NOT read or mutate that guild's music state

#### Scenario: Reject request when not authenticated
- **WHEN** an unauthenticated client requests any `/api/music/*` route or connects to `/ws/music/{guild_id}`
- **THEN** the plugin SHALL reject the request with a 401 response (or close the WebSocket) and SHALL NOT expose any music state

#### Scenario: Allow request for a guild the user belongs to
- **WHEN** an authenticated panel user submits a request targeting a `guild_id` that is present in the user's Discord guild list
- **THEN** the plugin SHALL process the request normally

#### Scenario: Authorize every route and WebSocket endpoint
- **WHEN** any music web route (`/plugin/music`, `/api/music/status/{guild_id}`, `/api/music/play`, `/api/music/controls/{action}`, `/api/music/volume`, `/api/music/repeat`, `/api/music/shuffle`, `/api/music/queue/remove`, `/api/music/queue/reorder`, `/api/music/queue/{guild_id}`, `/api/music/queue`, `/api/music/search/suggestions`, `/api/music/sources`) or the `/ws/music/{guild_id}` WebSocket is invoked
- **THEN** the plugin SHALL perform the guild authorization check before returning guild data or applying a control action

### Requirement: Music Plugin Test Coverage
The plugin SHALL be covered by unit tests for its commands and web routes, including authorization, volume bounds, and WebSocket broadcast behavior.

#### Scenario: Command behavior is tested
- **WHEN** the test suite runs
- **THEN** tests under `tests/unit/plugins/music/` SHALL cover playback commands (including seek and position WebSocket broadcast), queue management, voice control, and volume bounds

#### Scenario: Web route authorization is tested
- **WHEN** the test suite runs
- **THEN** tests SHALL assert that requests for guilds the user does not belong to are rejected, that unauthenticated requests are rejected, and that authorized requests succeed

## MODIFIED Requirements

### Requirement: Web Panel Integration
The plugin SHALL provide a web panel with WebSocket support for real-time music status and controls, with every route and WebSocket endpoint authorized against the authenticated user's Discord guild membership.

#### Scenario: Serve music panel interface
- **WHEN** an authenticated user accesses `/plugin/music` route
- **THEN** the plugin SHALL render the panel.html template scoped to the guilds the user belongs to

#### Scenario: Provide music status via REST API
- **WHEN** an authenticated client requests `/api/music/status/{guild_id}` for a guild the user belongs to
- **THEN** the plugin SHALL return JSON with connected state, current track, queue, volume, repeat mode, and shuffle status

#### Scenario: Handle WebSocket connections
- **WHEN** an authenticated client connects to `/ws/music/{guild_id}` for a guild the user belongs to
- **THEN** the MusicWebSocketManager SHALL accept the connection, send initial status, and handle ping/pong keepalive

#### Scenario: Reject unauthorized WebSocket connection
- **WHEN** a client connects to `/ws/music/{guild_id}` for a guild the user does not belong to or is not authenticated
- **THEN** the plugin SHALL close the WebSocket without sending music state

#### Scenario: Broadcast music updates
- **WHEN** music state changes (track start/end, queue update, playback control, seek, position)
- **THEN** the plugin SHALL broadcast the update to all WebSocket clients for the guild

#### Scenario: Handle web playback controls
- **WHEN** an authenticated user submits a POST request to `/api/music/controls/{action}` with a `guild_id` the user belongs to
- **THEN** the plugin SHALL execute the action (play/pause/stop/skip/previous), update state, save queue, and broadcast update

#### Scenario: Reject web control for unauthorized guild
- **WHEN** a POST request is made to `/api/music/controls/{action}` with a `guild_id` the user does not belong to
- **THEN** the plugin SHALL reject the request with a 403 response and SHALL NOT execute the action

#### Scenario: Enforce consistent volume bounds on the web panel
- **WHEN** an authenticated user submits a volume value to `/api/music/volume` for a guild they belong to
- **THEN** the plugin SHALL reject values outside the 0-100 range (matching the `/volume` Discord command) and SHALL apply values within that range, save state, and broadcast a volume update

#### Scenario: Define previous-track behavior
- **WHEN** an authenticated user invokes the previous-track control for a guild they belong to
- **THEN** the plugin SHALL either play the most recent history entry using the existing history system and broadcast an update, or the previous-track control SHALL be removed from the panel UI so no dead control is presented

### Requirement: Playback Control Commands
The plugin SHALL provide commands for controlling music playback with queue management, and SHALL keep the web panel in sync by broadcasting WebSocket updates for state-changing commands.

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
- **THEN** the bot SHALL validate the position is within track bounds, seek to that position, and broadcast a WebSocket playback update so the web panel position reflects the new seek point

#### Scenario: Display current track position
- **WHEN** a user invokes `/position`
- **THEN** the bot SHALL display a progress bar with current position, duration, and percentage complete, and SHALL broadcast a WebSocket playback update so the web panel position stays in sync
