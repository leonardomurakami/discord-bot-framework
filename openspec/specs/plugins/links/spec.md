## Purpose
Provides a link management system with default system links (GitHub, panel, docs, support) and guild-specific custom links stored in the database with CRUD operations.

## Requirements

### Requirement: Default Link Commands
The plugin SHALL provide default system link commands that display enhanced embeds with project-specific information.

#### Scenario: Display GitHub repository link
- **WHEN** a user invokes the `/github` command (or aliases `gh`, `source`)
- **THEN** the bot SHALL display an embed with the GitHub repository URL, contribution options, and GitHub-branded styling (color 0x24292F)

#### Scenario: Display web control panel link
- **WHEN** a user invokes the `/panel` command
- **THEN** the bot SHALL display an embed with the web panel URL, feature list, and Discord blurple color (0x5865F2)

#### Scenario: Display documentation link
- **WHEN** a user invokes the `/docs` command
- **THEN** the bot SHALL display an embed with documentation URL, setup guides, and green color (0x00D4AA)

#### Scenario: Display support server link
- **WHEN** a user invokes the `/support` command
- **THEN** the bot SHALL display an embed with the Discord server invite and community support information

### Requirement: Custom Link Management
The plugin SHALL allow users with appropriate permissions to create, view, and manage guild-specific custom links stored in the database.

#### Scenario: Display a custom link by name
- **WHEN** a user invokes `/link <name>` with a valid custom link name
- **THEN** the bot SHALL display an embed with the link URL, description, creation timestamp, and creator information

#### Scenario: List all custom links for a guild
- **WHEN** a user invokes the `/links` command in a server
- **THEN** the bot SHALL display an embed listing all custom links with descriptions and footer with usage instructions

#### Scenario: Add a new custom link
- **WHEN** a user with `links.collection.manage` permission invokes `/addlink <name> <url> [description]` with a valid HTTP/HTTPS URL and non-reserved name
- **THEN** the bot SHALL validate the URL format, check for reserved names, store the link in the database, and display a success embed

#### Scenario: Remove a custom link
- **WHEN** a user with `links.collection.manage` permission invokes `/removelink <name>` for an existing custom link
- **THEN** the bot SHALL delete the link from the database and display a confirmation embed

### Requirement: Link Configuration
The plugin SHALL load default links from configuration and enforce naming constraints.

#### Scenario: Load default links from config
- **WHEN** the LinksPlugin initializes
- **THEN** the plugin SHALL load default_links from links_settings containing github, panel, docs, and support URLs

#### Scenario: Prevent reserved name conflicts
- **WHEN** a user attempts to add a custom link with a reserved name (github, docs, panel, support, links, link, addlink, removelink)
- **THEN** the bot SHALL reject the request with an error message indicating the name is reserved

#### Scenario: Enforce unique link names per guild
- **WHEN** a user attempts to add a custom link with a name that already exists in the guild
- **THEN** the bot SHALL reject the request with an IntegrityError message indicating the link already exists

### Requirement: Permission-Based Access Control
The plugin SHALL enforce permission nodes for different link operations.

#### Scenario: View default and custom links
- **WHEN** a user with `basic.links.view` permission invokes any link viewing command
- **THEN** the bot SHALL allow the operation and display the requested link information

#### Scenario: Manage custom links
- **WHEN** a user with `links.collection.manage` permission invokes addlink or removelink
- **THEN** the bot SHALL allow the CRUD operations on custom links
