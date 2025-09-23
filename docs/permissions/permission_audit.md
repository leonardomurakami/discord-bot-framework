# Permission Audit Report

This document captures the results of the repository-wide permission review. Every plugin was inspected to catalogue existing
permission nodes, identify inconsistencies, and realign them with the new naming standard of `<plugin>.<category>.<action>` while
reserving the `basic.` prefix for commands that should be universally available.

## Summary
- All legacy permission nodes were catalogued and mapped to the new hierarchy.
- `basic.` nodes now explicitly encode plugin context (for example `basic.music.queue.view`).
- Management and administration actions now live under their owning plugin (for example `music.voice.manage` instead of
  `moderation.music.manage`).
- The `PermissionManager` was updated to understand the new hierarchy, wildcard matching rules, and database category labels.
- Plugin-wide aggregators (`admin.manage`, `moderation.manage`, `music.manage`, `links.manage`) allow roles to inherit full
  access without enumerating every sub-permission.

## Old → New Permission Mapping

| Plugin | Legacy Node | Replacement Node(s) | Notes |
| --- | --- | --- | --- |
| Admin | `admin.permissions` | `admin.permissions.manage` | Clarifies that the command grants management rights. |
| Admin | `admin.config` | `admin.config.manage` | Covers both prefix and autorole configuration commands. |
| Admin | `admin.plugins` | `admin.plugins.manage` | Reserved for future plugin lifecycle commands. |
| Music | `admin.music.settings` | `music.settings.manage` | Ownership moved to the music plugin namespace. |
| Help | `basic.commands` | `basic.help.commands.view` | Exposes command listings to everyone by default. |
| Help | `basic.plugins` | `basic.help.plugins.view` | Mirrors the command list node for plugin listings. |
| Utility | `basic.convert` | `basic.utility.convert.use` | Groups timestamp/base64 conversions under the utility plugin. |
| Utility | `basic.tools` | `basic.utility.tools.use` | Covers QR codes, reminders, polls, and related tools. |
| Utility | `basic.info` | `basic.utility.info.view` | Applies to user info, avatar, and weather lookups. |
| Fun | `basic.games` | `basic.fun.games.play` | Shared node for all mini-games, trivia, and RNG commands. |
| Fun | `basic.images` | `basic.fun.images.view` | Used by meme/image fetching commands. |
| Links | `links.view` | `basic.links.view` | Marked as universally accessible link browsing. |
| Links | `links.manage` | `links.collection.manage`, `links.manage` | Separate CRUD actions from the optional plugin-wide aggregator. |
| Moderation | `moderation.kick` | `moderation.members.kick` | Member management permissions are grouped under `members`. |
| Moderation | `moderation.ban` | `moderation.members.ban` | Applies to both ban and unban commands. |
| Moderation | `moderation.timeout` | `moderation.members.timeout` | |
| Moderation | `moderation.warn` | `moderation.members.warn` | |
| Moderation | `moderation.nickname` | `moderation.members.nickname` | |
| Moderation | `moderation.mute` | `moderation.members.mute` | Reserved for future mute support. |
| Moderation | `moderation.purge` | `moderation.channels.purge` | Channel-scoped actions grouped under `channels`. |
| Moderation | `moderation.slowmode` | `moderation.channels.slowmode` | |
| Music | `moderation.music.manage` | `music.queue.manage`, `music.voice.manage` | Split responsibilities between queue control and voice lifecycle. |
| Music | `music.play` | `basic.music.playback.control` | Default playback commands (play, pause, resume, etc.). |
| Music | `basic.music.play` | `basic.music.playback.control`, `basic.music.queue.view`, `basic.music.queue.control`, `basic.music.voice.control`, `basic.music.search.use` | Former catch-all node replaced by specific contexts. |
| Music | `music.manage` | `music.queue.manage`, `music.voice.manage` | Distinguishes queue vs. voice administrative actions. |
| Music | `music.settings` | `music.settings.manage` | |

## Newly Introduced Nodes

In addition to the replacements above, the review surfaced several new descriptive nodes to express fine-grained intent:

- `basic.music.queue.control` – shuffle/loop style queue controls that remain open to everyone.
- `basic.music.queue.view` – queue/history/now-playing viewers.
- `basic.music.voice.control` – joining channels and adjusting volume.
- `basic.music.search.use` – interactive track search picker.
- `music.voice.manage` – controlled disconnect operations.
- `basic.links.view` – highlights that link browsing is public by default.
- `basic.admin.info.view` – grants default access to telemetry commands such as `/bot-info` and `/server-info`.
- `basic.admin.status.view` – default uptime/status visibility.
- `admin.manage`, `moderation.manage`, `music.manage`, `links.manage` – high-level aggregators that grant the entire plugin's
  permission set when assigned to a role.

These nodes are discoverable by the permission discovery system and are documented per plugin in the updated AGENTS guides.

## Next Steps
- Apply the migration guide (`docs/permissions/migration.md`) to update any existing database rows or role assignments that still
  reference the legacy nodes.
- Audit any third-party plugins to ensure they follow the same hierarchy before deployment.
- Update provisioning scripts or infrastructure automation to seed the new nodes where required.
