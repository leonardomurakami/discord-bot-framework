## Purpose
The Typer CLI provides command-line interface for running the Discord bot, managing database tables, listing plugins, and scaffolding new bot projects.

## Requirements

### Requirement: Run Command with Development Mode
The CLI run command SHALL support a --dev flag to set the environment to development mode.

#### Scenario: Development mode is enabled via --dev flag
- **WHEN** run command is executed with --dev flag
- **THEN** the ENVIRONMENT environment variable SHALL be set to "development"

### Requirement: Run Command with Custom Log Level
The CLI run command SHALL support a --log-level option to override the default logging configuration.

#### Scenario: Log level is customized via --log-level option
- **WHEN** run command is executed with --log-level option
- **THEN** the LOG_LEVEL environment variable SHALL be set to the provided value and logging SHALL be configured with that level

### Requirement: Logging Configuration on Launch
The CLI SHALL configure logging with the specified level, format, and stream handler before bot initialization.

#### Scenario: Logging is configured before bot startup
- **WHEN** setup_logging is called with a level parameter
- **THEN** logging.basicConfig SHALL be called with the specified level, format "%(asctime)s - %(name)s - %(levelname)s - %(message)s", and StreamHandler output

### Requirement: Bot Instantiation and Execution
The run command SHALL instantiate DiscordBot and start the gateway connection.

#### Scenario: Bot is created and started via run command
- **WHEN** run command is executed
- **THEN** a DiscordBot instance SHALL be created and bot.run() SHALL be called to start the gateway

### Requirement: Database Table Creation
The CLI db command with create action SHALL create all database tables through the database manager.

#### Scenario: Database tables are created via db create command
- **WHEN** db command is executed with "create" action
- **THEN** db_manager.create_tables() SHALL be called asynchronously and a success message SHALL be displayed

### Requirement: Database Reset with Confirmation
The CLI db command with reset action SHALL drop all tables, recreate them, and require user confirmation before proceeding.

#### Scenario: Database is reset via db reset command with confirmation
- **WHEN** db command is executed with "reset" action and user confirms
- **THEN** db_manager.drop_tables() and db_manager.create_tables() SHALL be called asynchronously and a success message SHALL be displayed

### Requirement: Plugin Listing
The CLI plugins command with list action SHALL display all discovered plugins from configured directories with their enabled status.

#### Scenario: Plugins are listed via plugins list command
- **WHEN** plugins command is executed with "list" action
- **THEN** the CLI SHALL iterate through settings.plugin_directories, check for __init__.py in subdirectories, and display each plugin name with a checkmark if in settings.enabled_plugins or a cross otherwise

### Requirement: Project Initialization
The CLI init command SHALL scaffold a new bot project with required directory structure and .env configuration file.

#### Scenario: New bot project is scaffolded via init command
- **WHEN** init command is executed with optional directory parameter
- **THEN** the target directory SHALL be created with plugins/ and data/ subdirectories, and a .env file SHALL be created with DISCORD_TOKEN, BOT_PREFIX, DATABASE_URL, ENVIRONMENT, and LOG_LEVEL variables

### Requirement: CLI Help and Metadata
The Typer app SHALL be configured with appropriate name, help text, and disabled shell completion.

#### Scenario: CLI app is configured with metadata
- **WHEN** the Typer app is instantiated
- **THEN** the app SHALL have name "discord-bot", help text "Modular Discord Bot Framework", and add_completion set to False
