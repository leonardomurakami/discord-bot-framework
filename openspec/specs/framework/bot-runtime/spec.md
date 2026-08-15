## Purpose
The DiscordBot class provides the core runtime lifecycle for the Discord bot framework, managing initialization of all subsystems, gateway event subscriptions, and graceful shutdown procedures.

## Requirements

### Requirement: Bot Initialization with Required Intents
The DiscordBot constructor SHALL initialize the Hikari GatewayBot with all required intents for message, guild, member, and voice functionality.

#### Scenario: Constructor sets up gateway with comprehensive intents
- **WHEN** DiscordBot is instantiated
- **THEN** the hikari_bot SHALL be created with intents including ALL_MESSAGES, GUILD_MEMBERS, GUILDS, MESSAGE_CONTENT, and GUILD_VOICE_STATES

### Requirement: Subsystem Initialization
The DiscordBot constructor SHALL initialize all core subsystems including database manager, event system, message handler, plugin loader, permission manager, and web panel manager.

#### Scenario: Core subsystems are instantiated during bot construction
- **WHEN** DiscordBot.__init__ executes
- **THEN** self.db SHALL be set to db_manager, self.event_system to EventSystem(), self.message_handler to MessageCommandHandler(self), self.plugin_loader to PluginLoader(self), self.permission_manager to PermissionManager(self.db), and self.web_panel_manager to WebPanelManager(self)

### Requirement: Service Registry Registration
The DiscordBot SHALL register all core services in a service registry for dynamic dependency access by plugins.

#### Scenario: Core services are registered in service registry
- **WHEN** _register_core_services is called during initialization
- **THEN** self.services SHALL contain entries for "gateway", "command_client", "miru", "db", "events", "message_handler", "plugin_loader", "permissions", and "web_panel"

### Requirement: Gateway Event Subscription
The DiscordBot SHALL subscribe to all required Hikari gateway events for lifecycle management and message handling.

#### Scenario: Lifecycle events are subscribed during setup
- **WHEN** _setup_event_listeners is called
- **THEN** the hikari_bot SHALL have listeners for StartingEvent, StartedEvent, ShardReadyEvent, StoppingEvent, GuildAvailableEvent, GuildUnavailableEvent, MemberCreateEvent, MemberDeleteEvent, and GuildMessageCreateEvent

### Requirement: System Initialization Sequence
The bot SHALL initialize core systems in a specific sequence after the gateway starts: database tables, permissions, plugins, plugin tables, permission refresh, web panel, and startup tasks.

#### Scenario: Systems initialize in correct order after gateway start
- **WHEN** hikari.StartedEvent is received
- **THEN** _initialize_systems SHALL execute db.create_core_tables(), permission_manager.initialize(), _load_plugins(), db.create_plugin_tables(), permission_manager.refresh_permissions(), web_panel_manager.start(), and all tasks in _startup_tasks

### Requirement: Plugin Loading from Configuration
The plugin loader SHALL discover plugins from configured directories and load only those specified in settings.enabled_plugins.

#### Scenario: Enabled plugins are loaded from configured directories
- **WHEN** _load_plugins is called during system initialization
- **THEN** plugin_loader SHALL discover plugins from settings.plugin_directories and load only plugins listed in settings.enabled_plugins that were successfully discovered

### Requirement: Guild Prefix Resolution
The bot SHALL retrieve guild-specific prefixes from the database and fall back to the default bot prefix when no custom prefix is configured.

#### Scenario: Guild prefix is retrieved with fallback to default
- **WHEN** get_guild_prefix is called with a guild_id
- **THEN** the method SHALL query the Guild table for that guild_id and return the stored prefix if found, otherwise return settings.bot_prefix

### Requirement: Message Forwarding to Prefix Handler
The bot SHALL forward guild messages to the message handler for prefix command processing and emit message_create events for unhandled messages.

#### Scenario: Guild messages are processed by message handler
- **WHEN** hikari.GuildMessageCreateEvent is received
- **THEN** the bot SHALL call message_handler.handle_message(event) and if not handled, emit "message_create" event through event_system

### Requirement: Startup Task Registration
The bot SHALL allow registration of startup tasks that execute after all core systems are initialized.

#### Scenario: Startup tasks are registered and executed
- **WHEN** add_startup_task is called with a coroutine function
- **THEN** the task SHALL be appended to _startup_tasks list and executed during _initialize_systems after web panel startup

### Requirement: Graceful Shutdown Cleanup
The bot SHALL perform cleanup operations in sequence when stopping: emit stopping event, stop web panel, unload all plugins, and close database connection.

#### Scenario: Cleanup runs in sequence on bot shutdown
- **WHEN** hikari.StoppingEvent is received
- **THEN** _cleanup SHALL emit "bot_stopping" event, call web_panel_manager.stop(), unload all plugins via plugin_loader.unload_plugin, and call db.close()

### Requirement: Bot Readiness State Management
The bot SHALL track readiness state and emit a bot_ready event when the first shard becomes ready.

#### Scenario: Bot ready state is set on first shard ready
- **WHEN** hikari.ShardReadyEvent is received and is_ready is False
- **THEN** the bot SHALL set is_ready to True, log the bot user, and emit "bot_ready" event through event_system
