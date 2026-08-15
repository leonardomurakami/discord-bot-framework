## Purpose
Provides administrative commands for bot management including permission management, server configuration, auto-role assignment, and informational commands about the bot and server.

## Requirements

### Requirement: Permission Management
The plugin SHALL provide commands to list, grant, and revoke permission nodes for roles with wildcard support and pagination for large sets.

#### Scenario: List role permissions
- **WHEN** user runs `/permission list @role`
- **THEN** plugin SHALL display granted permissions for the role, using Miru pagination if more than 10 permissions

#### Scenario: Grant permission to role
- **WHEN** user runs `/permission grant @role moderation.*`
- **THEN** plugin SHALL grant all matching permission nodes to the role via PermissionManager, display success message with count of granted permissions, and log command usage

#### Scenario: Revoke permission from role
- **WHEN** user runs `/permission revoke @role moderation.ban`
- **THEN** plugin SHALL revoke the permission node from the role, display success message, and log command usage

#### Scenario: List all available permissions
- **WHEN** user runs `/permission list` without role
- **THEN** plugin SHALL display all available permissions with pagination (10 per page)

### Requirement: Prefix Configuration
The plugin SHALL provide a command to view and set the guild-specific command prefix with validation.

#### Scenario: View current prefix
- **WHEN** user runs `/prefix` without arguments
- **THEN** plugin SHALL display the current guild prefix with usage examples

#### Scenario: Set new prefix
- **WHEN** user runs `/prefix !`
- **THEN** plugin SHALL validate prefix length (max 5 characters), disallow quotes/backticks/whitespace, update Guild record in database, and display success message

#### Scenario: Invalid prefix
- **WHEN** user runs `/prefix "invalid"`
- **THEN** plugin SHALL reject the prefix with error message explaining validation rules

### Requirement: Auto-Role Configuration
The plugin SHALL provide commands to manage roles automatically assigned to new members with hierarchy validation.

#### Scenario: Add auto role
- **WHEN** user runs `/autorole add @role`
- **THEN** plugin SHALL validate bot role hierarchy (bot must be higher than target role), add role ID to guild settings, and display success message

#### Scenario: Remove auto role
- **WHEN** user runs `/autorole remove @role`
- **THEN** plugin SHALL remove role ID from guild settings and display success message

#### Scenario: List auto roles
- **WHEN** user runs `/autorole list`
- **THEN** plugin SHALL display all configured auto roles with role mentions

#### Scenario: Clear all auto roles
- **WHEN** user runs `/autorole clear`
- **THEN** plugin SHALL clear the autoroles list in guild settings and display success message

#### Scenario: Auto role assignment on join
- **WHEN** a new member joins a guild with configured auto roles
- **THEN** plugin SHALL automatically assign all configured roles to the member and log successful assignments

### Requirement: Bot Information
The plugin SHALL provide a command to display bot statistics and metadata.

#### Scenario: View bot info
- **WHEN** user runs `/bot-info`
- **THEN** plugin SHALL display embed with bot username, guild count, plugin count, database status, and creation date

### Requirement: Server Information
The plugin SHALL provide a command to display detailed server statistics and features.

#### Scenario: View server info
- **WHEN** user runs `/server-info`
- **THEN** plugin SHALL display embed with server ID, owner, creation date, member count, channel breakdown, role count, emoji count, and server features (Community, Verified, Partnered, etc.)

### Requirement: Uptime and System Status
The plugin SHALL provide a command to display bot uptime and system information with optional psutil integration.

#### Scenario: View uptime with psutil
- **WHEN** user runs `/uptime` and psutil is installed
- **THEN** plugin SHALL display embed with uptime duration, start time, current time, memory usage, CPU usage, system uptime, server count, and gateway latency

#### Scenario: View uptime without psutil
- **WHEN** user runs `/uptime` and psutil is not installed
- **THEN** plugin SHALL display embed with basic uptime info, server count, gateway latency, and footer suggesting psutil installation

### Requirement: Web Panel Integration
The plugin SHALL provide a web panel at /plugin/admin for permission management via FastAPI routes.

#### Scenario: Access admin panel
- **WHEN** authenticated user with Discord admin access accesses /plugin/admin
- **THEN** plugin SHALL render panel.html with permissions grouped by category and guild selection interface

#### Scenario: Get guild roles via API
- **WHEN** web client calls GET /plugin/admin/api/guild/{guild_id}/roles
- **THEN** plugin SHALL return HTML with role list sorted by position, excluding @everyone

#### Scenario: Grant permission via API
- **WHEN** web client calls POST /plugin/admin/api/guild/{guild_id}/role/{role_id}/permissions/grant
- **THEN** plugin SHALL validate guild admin access, grant permission via PermissionManager, and return JSON with success status and granted/failed counts
