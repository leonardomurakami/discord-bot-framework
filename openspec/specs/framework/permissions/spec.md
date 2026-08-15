## Purpose
Provides a role-based permission system with caching, hierarchical rules, wildcard support, and decorators for protecting Discord bot commands and features.

## Requirements

### Requirement: Permission caching per guild role
The PermissionManager SHALL cache granted permission nodes per guild role to minimize database queries.

#### Scenario: Cache role permissions on first check
- **WHEN** a permission check is performed for a user in a guild
- **THEN** the PermissionManager stores the fetched role permissions in `_permission_cache[guild_id][role_id]` for subsequent checks

### Requirement: Default permission seeding from plugins
The PermissionManager SHALL discover and create default permissions from loaded plugins during initialization.

#### Scenario: Discover permissions from plugin commands
- **WHEN** the PermissionManager initializes via `initialize()`
- **THEN** it scans all loaded plugins for `_unified_command` metadata and `PLUGIN_METADATA["permissions"]` to create missing Permission records in the database

### Requirement: Hierarchy rules for manage and admin nodes
The PermissionManager SHALL treat `.manage` and `.admin` permission nodes as granting access to their entire namespace.

#### Scenario: Grant namespace access via manage node
- **WHEN** a role has permission `music.manage` granted
- **THEN** the user with that role is granted access to all permission nodes starting with `music.` or `basic.music.`

### Requirement: Wildcard pattern support
The PermissionManager SHALL support wildcard patterns for granting and revoking permissions.

#### Scenario: Grant permissions with suffix wildcard
- **WHEN** `grant_permission()` is called with pattern `moderation.*`
- **THEN** all permission nodes matching the pattern (e.g., `moderation.kick`, `moderation.ban`) are granted to the role

#### Scenario: Grant permissions with prefix wildcard
- **WHEN** `grant_permission()` is called with pattern `*.play`
- **THEN** all permission nodes ending with `.play` (e.g., `music.play`, `audio.play`) are granted to the role

### Requirement: Decorator for permission node checking
The framework SHALL provide a `requires_permission` decorator to protect command handlers.

#### Scenario: Deny access without required permission
- **WHEN** a command decorated with `@requires_permission("admin.ban")` is invoked by a user lacking that permission
- **THEN** the decorator responds with an ephemeral error message and prevents the handler from executing

### Requirement: Decorator for role-based access
The framework SHALL provide a `requires_role` decorator to restrict commands to specific Discord roles.

#### Scenario: Deny access without required role
- **WHEN** a command decorated with `@requires_role(123456789)` is invoked by a user without that role ID
- **THEN** the decorator responds with an ephemeral error message and prevents the handler from executing

### Requirement: Decorator for guild owner restriction
The framework SHALL provide a `requires_guild_owner` decorator to restrict commands to server owners.

#### Scenario: Deny access to non-owners
- **WHEN** a command decorated with `@requires_guild_owner()` is invoked by a non-owner user
- **THEN** the decorator responds with an ephemeral error message and prevents the handler from executing

### Requirement: Decorator for bot permission checking
The framework SHALL provide a `requires_bot_permissions` decorator to verify the bot has required Discord permissions.

#### Scenario: Deny execution when bot lacks permissions
- **WHEN** a command decorated with `@requires_bot_permissions(hikari.Permissions.MANAGE_MESSAGES)` is invoked in a guild where the bot lacks that permission
- **THEN** the decorator responds with an ephemeral error message listing missing permissions and prevents the handler from executing

### Requirement: Grant and revoke operations
The PermissionManager SHALL support granting and revoking permissions for both roles and users with wildcard pattern resolution.

#### Scenario: Grant permission to role
- **WHEN** `grant_permission(guild_id, role_id, "music.play")` is called
- **THEN** a RolePermission record is created or updated with `granted=True` and the guild cache is cleared

#### Scenario: Revoke permission from user
- **WHEN** `revoke_user_permission(guild_id, user_id, "admin.*")` is called
- **THEN** matching UserPermission records are updated with `granted=False` and the results are returned

### Requirement: Cache invalidation
The PermissionManager SHALL invalidate cached permissions when grants or revokes occur.

#### Scenario: Clear guild cache on permission change
- **WHEN** `grant_permission()` or `revoke_permission()` successfully modifies permissions
- **THEN** `_clear_guild_cache(guild_id)` is called to remove the guild's cached permissions

### Requirement: Server owner and administrator bypass
The PermissionManager SHALL automatically grant all permissions to server owners and users with Discord Administrator permission.

#### Scenario: Server owner bypass
- **WHEN** `has_permission()` is called for a user whose ID matches `guild.owner_id`
- **THEN** the method returns True without checking role or user permissions

#### Scenario: Administrator permission bypass
- **WHEN** `has_permission()` is called for a user with the Administrator Discord permission
- **THEN** the method returns True without checking role or user permissions

### Requirement: Default basic permissions
The PermissionManager SHALL grant all permissions starting with `basic.` to all users by default.

#### Scenario: Allow basic command access
- **WHEN** `has_permission()` is called for a permission node starting with `basic.`
- **THEN** the method returns True regardless of role or user grants
