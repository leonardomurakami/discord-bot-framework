## ADDED Requirements

### Requirement: Web Panel Section Navigation
The admin web panel SHALL organise its features into distinct, navigable sections (e.g. tabs or a sidebar) so that permission management, prefix management, autorole management, bot info, server info, and uptime/status are each reachable without leaving the panel.

#### Scenario: Switch between panel sections
- **WHEN** an authenticated guild admin selects a different section within /plugin/admin
- **THEN** the panel SHALL display that section's content without a full page reload and SHALL preserve the currently selected guild context

#### Scenario: Default section on load
- **WHEN** an authenticated guild admin opens /plugin/admin
- **THEN** the panel SHALL load the permission management section by default and SHALL make all other sections reachable from the initial view

### Requirement: Web Prefix Management
The admin web panel SHALL provide a form to view and set the guild command prefix with the same validation rules as the `/prefix` command.

#### Scenario: View current prefix
- **WHEN** an authenticated guild admin opens the prefix section for a guild
- **THEN** the panel SHALL display the guild's current prefix and the validation rules (max 5 characters, no quotes/backticks/whitespace)

#### Scenario: Set valid prefix via API
- **WHEN** the web client submits a new prefix to POST /plugin/admin/api/guild/{guild_id}/prefix that is 1-5 characters and contains no quotes, backticks, or whitespace
- **THEN** the plugin SHALL validate guild admin access, update the Guild record in the database, and return JSON confirming the new prefix

#### Scenario: Reject invalid prefix via API
- **WHEN** the web client submits a prefix that exceeds 5 characters, is empty/whitespace-only, or contains quotes/backticks/whitespace
- **THEN** the plugin SHALL reject the change with a 400 response and an error message explaining the validation rules

#### Scenario: Unauthenticated prefix change
- **WHEN** an unauthenticated request is sent to the prefix API
- **THEN** the plugin SHALL return 401 and SHALL NOT modify the prefix

### Requirement: Web Auto-Role Management
The admin web panel SHALL provide a list of current autoroles with add and remove controls, enforcing the same role hierarchy validation as the `/autorole` command.

#### Scenario: List current autoroles
- **WHEN** an authenticated guild admin opens the autorole section for a guild
- **THEN** the panel SHALL display all configured autoroles by name, or an empty state when none are configured

#### Scenario: Add autorole via API
- **WHEN** the web client submits a role to POST /plugin/admin/api/guild/{guild_id}/autoroles
- **THEN** the plugin SHALL validate guild admin access, verify the bot's highest role is above the target role, add the role ID to guild settings, and return JSON confirming the addition

#### Scenario: Reject autorole add on hierarchy violation
- **WHEN** the web client submits a role whose position is greater than or equal to the bot's highest role
- **THEN** the plugin SHALL reject the addition with a 400 response and an error message explaining the hierarchy requirement, and SHALL NOT persist the role

#### Scenario: Remove autorole via API
- **WHEN** the web client submits DELETE /plugin/admin/api/guild/{guild_id}/autoroles/{role_id}
- **THEN** the plugin SHALL remove the role ID from guild settings and return JSON confirming the removal

#### Scenario: Add duplicate autorole
- **WHEN** the web client submits a role that is already configured as an autorole
- **THEN** the plugin SHALL reject the addition with a 400 response indicating the role is already configured

### Requirement: Web Bot Information View
The admin web panel SHALL provide a read-only view of bot statistics and metadata equivalent to the `/bot-info` command.

#### Scenario: View bot info
- **WHEN** an authenticated guild admin opens the bot info section
- **THEN** the panel SHALL display the bot username, guild count, plugin count, database connection status, and bot creation date

#### Scenario: Bot info is read-only
- **WHEN** the bot info section is rendered
- **THEN** the panel SHALL NOT present any controls that mutate bot state

### Requirement: Web Server Information View
The admin web panel SHALL provide a read-only view of the selected guild's statistics and features equivalent to the `/server-info` command.

#### Scenario: View server info
- **WHEN** an authenticated guild admin opens the server info section for a guild
- **THEN** the panel SHALL display the server ID, owner, creation date, member count, channel breakdown (text/voice/category), role count, emoji count, server features, and icon/banner where available

#### Scenario: Server info for unavailable guild
- **WHEN** the selected guild is not in the bot's cache
- **THEN** the panel SHALL display an informative empty state rather than an unhandled error

### Requirement: Web Uptime and Status View
The admin web panel SHALL provide a read-only view of bot uptime and system status equivalent to the `/uptime` command, degrading gracefully when psutil is unavailable.

#### Scenario: View status with psutil
- **WHEN** an authenticated guild admin opens the status section and psutil is installed
- **THEN** the panel SHALL display uptime duration, start time, current time, memory usage, CPU usage, system uptime, server count, gateway latency, and PID

#### Scenario: View status without psutil
- **WHEN** an authenticated guild admin opens the status section and psutil is not installed
- **THEN** the panel SHALL display basic uptime info, server count, gateway latency, and a note suggesting psutil installation, without raising an error

### Requirement: Configurable Default Prefix
When creating a guild record on demand, the admin web panel SHALL use the global configured default prefix (`settings.bot_prefix`) rather than a hardcoded value.

#### Scenario: Guild created from web panel uses configured default
- **WHEN** the web panel ensures a guild exists in the database for a guild that has no existing Guild record
- **THEN** the plugin SHALL create the Guild record with the prefix equal to the global config default prefix

### Requirement: Web Panel Output Escaping
All user-supplied values rendered into HTML by the admin web panel SHALL be escaped using a consistent escaping helper to prevent XSS, including single quotes.

#### Scenario: Role name with single quote
- **WHEN** the panel renders a role whose name contains a single quote
- **THEN** the plugin SHALL escape the quote via the shared escaping helper rather than stripping it with an ad-hoc character replacement, and the rendered output SHALL not break the surrounding markup

#### Scenario: Member display name with special characters
- **WHEN** the panel renders a member whose display name contains quotes, backticks, or angle brackets
- **THEN** the plugin SHALL escape the value via the shared escaping helper and the rendered output SHALL not execute any embedded markup

### Requirement: Admin Plugin Test Coverage
The admin plugin SHALL include automated tests covering the prefix command, autorole command (including hierarchy validation and on-join assignment), the web panel routes (prefix, autorole, bot info, server info, status), and the Miru pagination views.

#### Scenario: Prefix command tests
- **WHEN** the test suite runs
- **THEN** tests SHALL cover viewing the current prefix, setting a valid prefix, and rejecting invalid prefixes (too long, empty, disallowed characters)

#### Scenario: Autorole command tests
- **WHEN** the test suite runs
- **THEN** tests SHALL cover add, remove, list, clear, duplicate-add rejection, hierarchy-violation rejection, and automatic role assignment on member join

#### Scenario: Web panel route tests
- **WHEN** the test suite runs
- **THEN** tests SHALL cover the prefix, autorole, bot info, server info, and status endpoints including auth gating and validation errors

#### Scenario: Miru view tests
- **WHEN** the test suite runs
- **THEN** tests SHALL cover the permission and role-permission pagination views including page navigation and empty states
