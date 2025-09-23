# Moderation Plugin Guidelines

## Overview
- Provides core moderation tooling: kick/ban/unban, timeout, warn, nickname updates, message purging, and channel slowmode.
- Relies on built-in Discord permission checks (role hierarchy, bot permissions) and surfaces detailed error feedback via embeds.
- Primary permission nodes (granting plugin-wide access via `moderation.manage` plus fine-grained controls):
  - `moderation.manage` – assigns the full moderation toolset to a role.
  - `moderation.members.kick`
  - `moderation.members.ban`
  - `moderation.members.timeout`
  - `moderation.members.warn`
  - `moderation.members.nickname`
  - `moderation.members.mute` (reserved for future mute functionality)
  - `moderation.channels.purge`
  - `moderation.channels.slowmode`

## Architecture
- `plugin.py` instantiates the plugin and registers command factories from `commands/`.
- `commands/`
  - `actions.py` – member-centric actions (kick, ban/unban, timeout, nickname changes). Each command validates role hierarchy and
    uses `BasePlugin.smart_respond` for consistent messaging.
  - `discipline.py` – warning system (issue, list, clear) that records reasons with timestamps in embeds.
  - `channel.py` – channel management (bulk purge, enable/disable slowmode). Includes checks for bot permissions.
- Currently stateless; future persistence (e.g., warning history) can be introduced via `DatabaseMixin` if required.
- The package reserves `views/`, `models/`, and `web/` directories for future expansion but they are empty by default.

## Commands
| Command | Description | Permission Node |
| --- | --- | --- |
| `/kick <member> [reason]` | Kicks a member with audit log reason support. | `moderation.members.kick` |
| `/ban <member> [delete_days] [reason]` | Bans a member, optionally deleting recent messages. | `moderation.members.ban` |
| `/unban <user_id> [reason]` | Removes a ban. | `moderation.members.ban` |
| `/timeout <member> <duration> [reason]` | Applies Discord timeout for a specified duration. | `moderation.members.timeout` |
| `/nickname <member> <new_nick>` | Updates a member nickname, respecting hierarchy. | `moderation.members.nickname` |
| `/warn <member> <reason>` | Issues a warning. | `moderation.members.warn` |
| `/warnings <member>` | Lists stored warnings during runtime. | `moderation.members.warn` |
| `/clear-warnings <member>` | Clears warning history. | `moderation.members.warn` |
| `/purge <amount> [user]` | Bulk deletes messages from the current channel. | `moderation.channels.purge` |
| `/slowmode <channel> <delay>` | Enables or disables slowmode with validation. | `moderation.channels.slowmode` |

## Configuration
- No dedicated plugin configuration or environment variables. Commands rely on Discord's permissions and the shared bot settings.
- Duration parsing for timeouts leverages helper functions inside `commands/actions.py`; adjust there when supporting new formats.
- Embeds use color constants defined within each command file for consistency (e.g., success vs error states).

## Development Guidelines
- Maintain strong validation: check for guild context, ensure bot has the necessary permissions, and compare role hierarchy before
  executing actions. Existing commands demonstrate these checks.
- When adding new moderation actions, place them in the appropriate factory (`actions`, `discipline`, or `channel`) and return
  decorated coroutines that `plugin._register_commands()` will attach.
- Use `plugin.log_command_usage` to record success/failure analytics for new commands.
- If persistence is introduced (e.g., storing warnings), inherit from `DatabaseMixin`, define models in `models/`, and register them
  in `plugin.py`.
- Run focused tests: `uv run pytest tests/unit/plugins/moderation`.

## Troubleshooting
- **Command rejected with hierarchy error**: confirm the bot's highest role is above the target member and the invoking moderator has
  sufficient privileges.
- **No action occurs**: ensure the guild has granted the correct permission node to the moderator's role.
- **Timeout command fails**: Discord imposes min/max duration constraints; refer to the validation logic in `actions.py` for current
  limits.

## Examples
### Adding a soft-ban command
```python
@command(name="softban", description="Ban and immediately unban to delete messages", permission_node="moderation.members.ban")
async def softban(ctx: lightbulb.Context, member: hikari.Member, reason: str | None = None) -> None:
    await ctx.app.rest.ban_member(ctx.guild_id, member.id, delete_message_days=1, reason=reason)
    await ctx.app.rest.unban_member(ctx.guild_id, member.id, reason="Softban cleanup")
    await plugin.smart_respond(ctx, f"Softbanned {member.display_name} and cleared recent messages.")
```

### Granting purge rights
```python
# /permission grant @Moderators moderation.channels.purge
```

Use these guidelines to keep moderation actions safe, predictable, and aligned with Discord's permission model.
