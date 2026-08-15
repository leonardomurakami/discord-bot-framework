## Purpose
Provides a comprehensive help system with intelligent command search, plugin browsing, pagination, and interactive dropdown menus for navigating bot commands and plugin information.

## Requirements

### Requirement: General Help Overview
The plugin SHALL provide a main help command displaying bot statistics, plugin categories, and essential commands with interactive navigation.

#### Scenario: View general help
- **WHEN** user runs `/help` without arguments
- **THEN** plugin SHALL display embed with bot statistics (plugin count, command count, prefix), getting started tips, available plugin categories, essential commands, and attach PluginSelectWithPaginationView with dropdown

#### Scenario: General help with Miru unavailable
- **WHEN** user runs `/help` and Miru client is not available
- **THEN** plugin SHALL display embed without interactive components

### Requirement: Command-Specific Help
The plugin SHALL provide detailed help for specific commands when queried by name.

#### Scenario: Get help for specific command
- **WHEN** user runs `/help ping`
- **THEN** plugin SHALL search for command in message_handler, display embed with command name, description, usage with prefix, aliases, and required permission node

#### Scenario: Command not found
- **WHEN** user runs `/help nonexistent`
- **THEN** plugin SHALL display error embed suggesting use of `/help` without arguments

### Requirement: Plugin-Specific Help
The plugin SHALL provide help for specific plugins including metadata and command listings.

#### Scenario: Get help for specific plugin
- **WHEN** user runs `/help admin`
- **THEN** plugin SHALL find plugin by name, display embed with plugin name, description, version, author, commands list, and permission nodes

#### Scenario: Plugin not found
- **WHEN** user runs `/help nonexistent_plugin`
- **THEN** plugin SHALL display error embed

### Requirement: Commands List
The plugin SHALL provide a command to list all available commands organized by category.

#### Scenario: List all commands
- **WHEN** user runs `/commands`
- **THEN** plugin SHALL display embed with commands grouped by category (Help, Fun, Admin, Moderation, Other), showing command names grouped together

### Requirement: Plugins List
The plugin SHALL provide a command to list all loaded plugins with metadata.

#### Scenario: List all plugins
- **WHEN** user runs `/plugins`
- **THEN** plugin SHALL display embed with all loaded plugins showing name, version, and truncated description

### Requirement: Plugin Dropdown Navigation
The plugin SHALL provide an interactive dropdown menu for selecting plugins to view their commands.

#### Scenario: Select plugin from dropdown
- **WHEN** user selects a plugin from the dropdown in general help
- **THEN** view SHALL update embed to show plugin-specific commands with pagination, update dropdown options, and maintain pagination state

#### Scenario: Select "Home" from dropdown
- **WHEN** user selects "General Help" from dropdown
- **THEN** view SHALL return to the main help overview embed

### Requirement: Command Pagination
The plugin SHALL provide pagination for browsing plugin commands when there are more than fit on one page.

#### Scenario: Navigate to next page
- **WHEN** user clicks next page button
- **THEN** view SHALL generate embed for next page of commands (5 per page), update pagination info, and refresh embed

#### Scenario: Navigate to previous page
- **WHEN** user clicks previous page button
- **THEN** view SHALL generate embed for previous page of commands, update pagination info, and refresh embed

#### Scenario: Already on first/last page
- **WHEN** user clicks pagination button at boundary
- **THEN** view SHALL send ephemeral message indicating already at boundary

### Requirement: Persistent Views
The plugin SHALL register persistent Miru views that survive bot restarts for help navigation.

#### Scenario: Register persistent view on load
- **WHEN** plugin loads via on_load()
- **THEN** plugin SHALL create PersistentPluginSelectView and register with miru_client using start_view with bind_to=None

#### Scenario: Persistent view callback after restart
- **WHEN** user interacts with persistent help dropdown after bot restart
- **THEN** view SHALL resolve help plugin instance through multiple fallback methods (global bot instance, miru client app, context bot), handle selection, and update response

### Requirement: Command Information Management
The plugin SHALL provide a CommandInfoManager to retrieve and format command metadata.

#### Scenario: Get command info
- **WHEN** CommandInfoManager.get_command_info() is called with command name
- **THEN** it SHALL search commands by name and aliases, return dict with name, description, aliases, permission_node, usage, and plugin_name

#### Scenario: Get bot statistics
- **WHEN** CommandInfoManager.get_bot_statistics() is called
- **THEN** it SHALL return dict with plugin count, unique command count, and plugin category names

#### Scenario: Get essential commands
- **WHEN** CommandInfoManager.get_essential_commands() is called
- **THEN** it SHALL return list of essential command suggestions with emoji, prefix, and description

### Requirement: Embed Generation
The plugin SHALL provide EmbedGenerators class for creating consistent help embeds.

#### Scenario: Generate general help embed
- **WHEN** EmbedGenerators.get_general_help() is called
- **THEN** it SHALL create embed with bot statistics, getting started section, plugin categories, essential commands, and footer with tip

#### Scenario: Generate plugin commands embed
- **WHEN** EmbedGenerators.get_plugin_commands_embed() is called with plugin name and page
- **THEN** it SHALL create embed with plugin metadata, commands with usage and arguments (5 per page), pagination info in footer, and return tuple with pagination metadata

#### Scenario: Generate commands list embed
- **WHEN** EmbedGenerators.get_commands_list() is called
- **THEN** it SHALL create embed with commands grouped by category (Help, Fun, Admin, Moderation, Other)

### Requirement: Configuration
The plugin SHALL provide configurable settings for help display behavior.

#### Scenario: Configure pagination timeout
- **WHEN** HELP_PAGINATION_TIMEOUT_SECONDS is set in environment
- **THEN** plugin SHALL use this value for view timeout (default 300 seconds)

#### Scenario: Configure commands per page
- **WHEN** HELP_COMMANDS_PER_PAGE is set in environment
- **THEN** plugin SHALL use this value for pagination (default 10)

#### Scenario: Configure embed color
- **WHEN** HELP_EMBED_COLOR is set in environment
- **THEN** plugin SHALL use this hex value for embed color (default 0x5865F2)
