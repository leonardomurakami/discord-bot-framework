## Purpose
Provides comprehensive moderation tools including member actions (kick, ban, timeout, nickname), channel management (purge, slowmode, lockdown), and discipline tracking (warnings, moderator notes).

## Requirements

### Requirement: Member Action Commands
The plugin SHALL provide commands for member moderation actions with role hierarchy validation and audit logging.

#### Scenario: Kick a member from the server
- **WHEN** a moderator with `moderation.members.kick` permission invokes `/kick <member> [reason]`
- **THEN** the bot SHALL validate the target is not self or bot, send a DM to the member, execute the kick with audit reason, and log the action

#### Scenario: Ban a user from the server
- **WHEN** a moderator with `moderation.members.ban` permission invokes `/ban <user> [delete_days] [reason]`
- **THEN** the bot SHALL validate the target, optionally delete recent messages (1-7 days), send a DM if possible, execute the ban, and log the action

#### Scenario: Timeout a member for a duration
- **WHEN** a moderator with `moderation.members.timeout` permission invokes `/timeout <member> <duration> [reason]` with duration in minutes
- **THEN** the bot SHALL set the member's communication_disabled_until timestamp and display formatted duration (minutes/hours)

#### Scenario: Unban a user
- **WHEN** a moderator with `moderation.members.ban` permission invokes `/unban <user_id> [reason]`
- **THEN** the bot SHALL verify the user is in the ban list, remove the ban, and display confirmation with user information

#### Scenario: Change a member's nickname
- **WHEN** a moderator with `moderation.members.nickname` permission invokes `/nickname <member> [new_nickname]`
- **THEN** the bot SHALL update the member's nickname or remove it if empty, displaying the previous and new nickname

### Requirement: Channel Management Commands
The plugin SHALL provide commands for channel-level moderation including message purging and rate limiting.

#### Scenario: Purge messages from a channel
- **WHEN** a moderator with `moderation.channels.purge` permission invokes `/purge <amount> [user]` with amount between 1-100
- **THEN** the bot SHALL delete the specified number of messages (optionally filtered by user) and display the deletion count

#### Scenario: Set channel slowmode
- **WHEN** a moderator with `moderation.channels.slowmode` permission invokes `/slowmode [seconds] [channel]` with seconds between 0-21600
- **THEN** the bot SHALL set the channel's rate_limit_per_user and display the slowmode duration in human-readable format

#### Scenario: Lock or unlock a channel
- **WHEN** a moderator with `moderation.channels.slowmode` permission invokes `/lockdown <action> [channel] [reason]` with action "lock" or "unlock"
- **THEN** the bot SHALL modify the @everyone role's SEND_MESSAGES permission, store lockdown metadata in guild settings, and display confirmation

### Requirement: Discipline Tracking System
The plugin SHALL provide warning and moderator note tracking with persistent storage per guild.

#### Scenario: Issue a warning to a member
- **WHEN** a moderator with `moderation.members.warn` permission invokes `/warn <member> [reason]`
- **THEN** the bot SHALL store the warning with timestamp, moderator ID, and incrementing warning ID, send a DM to the member, and display total warning count

#### Scenario: View warnings for a member
- **WHEN** a moderator with `moderation.members.warn` permission invokes `/warnings [member]`
- **THEN** the bot SHALL display up to 5 most recent warnings with reasons, moderators, timestamps, and total count

#### Scenario: Add a moderator note
- **WHEN** a moderator with `moderation.members.warn` permission invokes `/modnote add <member> <note>`
- **THEN** the bot SHALL store the private note with timestamp and moderator ID in guild settings

#### Scenario: View moderator notes
- **WHEN** a moderator with `moderation.members.warn` permission invokes `/modnote view <member>`
- **THEN** the bot SHALL display up to 5 most recent notes with content, author, and timestamps

#### Scenario: Clear moderator notes
- **WHEN** a moderator with `moderation.members.warn` permission invokes `/modnote clear <member>`
- **THEN** the bot SHALL delete all stored notes for the member and display the count of removed notes

### Requirement: Moderation Configuration
The plugin SHALL load configuration constants for limits, colors, and display settings.

#### Scenario: Load moderation configuration
- **WHEN** the ModerationPlugin initializes
- **THEN** the plugin SHALL load color constants (ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR), limits (PURGE_MIN=1, PURGE_MAX=100, SLOWMODE_MAX_SECONDS=21600), and display limits (WARN_DISPLAY_LIMIT=5, NOTE_DISPLAY_LIMIT=5)

#### Scenario: Validate purge amount limits
- **WHEN** a user invokes `/purge` with an amount outside 1-100
- **THEN** the bot SHALL reject the request with an error message indicating valid range

#### Scenario: Validate slowmode duration limits
- **WHEN** a user invokes `/slowmode` with seconds outside 0-21600
- **THEN** the bot SHALL reject the request with an error message indicating the 6-hour maximum
