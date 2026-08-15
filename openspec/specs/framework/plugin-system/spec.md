## Purpose
Provides a modular plugin system for discovering, loading, and managing Discord bot plugins with automatic lifecycle management, dependency resolution, database model registration, and web panel integration.

## Requirements

### Requirement: Plugin Directory Discovery
The PluginLoader SHALL discover plugin packages from configured directories by scanning for subdirectories containing `__init__.py` files.

#### Scenario: Discover plugins from configured directories
- **WHEN** `PluginLoader.add_plugin_directory()` is called with a valid directory path
- **THEN** the directory SHALL be added to `plugin_directories` and logged
- **AND** `discover_plugins()` SHALL scan each directory for subdirectories not starting with underscore
- **AND** subdirectories with `__init__.py` SHALL be returned as discovered plugin names

#### Scenario: Handle invalid plugin directory
- **WHEN** `PluginLoader.add_plugin_directory()` is called with a non-existent or non-directory path
- **THEN** a warning SHALL be logged and the directory SHALL NOT be added to `plugin_directories`

### Requirement: Plugin Metadata Extraction
The PluginLoader SHALL extract plugin metadata from the `PLUGIN_METADATA` dictionary in plugin modules.

#### Scenario: Extract metadata from PLUGIN_METADATA
- **WHEN** a plugin module defines `PLUGIN_METADATA` with name, version, author, description, dependencies, and permissions
- **THEN** `_extract_metadata()` SHALL return a `PluginMetadata` instance with those values
- **AND** missing fields SHALL use defaults (version="1.0.0", author="Unknown", empty strings/dicts)

#### Scenario: Fallback metadata for plugins without PLUGIN_METADATA
- **WHEN** a plugin module does not define `PLUGIN_METADATA`
- **THEN** `_extract_metadata()` SHALL return a `PluginMetadata` instance with name set to the module name

### Requirement: Plugin Class Extraction
The PluginLoader SHALL extract the plugin class by finding BasePlugin subclasses or setup functions.

#### Scenario: Extract BasePlugin subclass
- **WHEN** a module contains a class inheriting from BasePlugin that is not BasePlugin itself
- **THEN** `_extract_plugin_class()` SHALL return that class
- **AND** the class MUST be defined in the same module as specified by `__module__`

#### Scenario: Extract setup function as fallback
- **WHEN** a module does not contain a BasePlugin subclass but has a `setup` function
- **THEN** `_extract_plugin_class()` SHALL return the setup function

#### Scenario: Fail when no plugin class found
- **WHEN** a module has neither a BasePlugin subclass nor a setup function
- **THEN** `_extract_plugin_class()` SHALL raise a ValueError

### Requirement: Dependency Validation
The PluginLoader SHALL validate that all declared plugin dependencies are loaded before loading a plugin.

#### Scenario: Load plugin with satisfied dependencies
- **WHEN** a plugin's metadata lists dependencies and all dependencies are already in `self.plugins`
- **THEN** `load_plugin()` SHALL proceed with loading the plugin

#### Scenario: Reject plugin with unsatisfied dependencies
- **WHEN** a plugin's metadata lists a dependency that is not in `self.plugins`
- **THEN** `load_plugin()` SHALL log an error and return False
- **AND** the plugin SHALL NOT be loaded

### Requirement: Plugin Load Lifecycle
The PluginLoader SHALL load plugins by instantiating the plugin class and calling on_load for initialization.

#### Scenario: Load plugin via class instantiation
- **WHEN** `_extract_plugin_class()` returns a class (not a setup function)
- **THEN** `load_plugin()` SHALL instantiate the class with the bot instance
- **AND** SHALL call `await plugin_instance.on_load()`
- **AND** SHALL store the instance in `self.plugins` and metadata in `self.plugin_metadata`

#### Scenario: Load plugin via setup function
- **WHEN** `_extract_plugin_class()` returns a setup function
- **THEN** `load_plugin()` SHALL call the setup function with the bot instance
- **AND** SHALL call `await plugin_instance.on_load()` on the returned instance
- **AND** SHALL store the instance and metadata

#### Scenario: Reject already loaded plugin
- **WHEN** `load_plugin()` is called with a plugin name already in `self.plugins`
- **THEN** the method SHALL log that the plugin is already loaded and return True

### Requirement: Plugin Unload Lifecycle
The PluginLoader SHALL unload plugins by calling on_unload and removing the plugin from tracking.

#### Scenario: Unload loaded plugin
- **WHEN** `unload_plugin()` is called with a loaded plugin name
- **THEN** the method SHALL call `await plugin.on_unload()`
- **AND** SHALL remove the plugin from `self.plugins` and metadata from `self.plugin_metadata`
- **AND** SHALL remove the module from `sys.modules` to allow reloading
- **AND** SHALL return True

#### Scenario: Fail to unload non-loaded plugin
- **WHEN** `unload_plugin()` is called with a plugin name not in `self.plugins`
- **THEN** the method SHALL log a warning and return False

### Requirement: BasePlugin Command Registration
BasePlugin SHALL automatically register slash and prefix commands during on_load via CommandRegistry.

#### Scenario: Register commands on load
- **WHEN** `BasePlugin.on_load()` is called
- **THEN** it SHALL call `await self._command_registry.register_commands()`
- **AND** the CommandRegistry SHALL register both slash and prefix commands

#### Scenario: Unregister commands on unload
- **WHEN** `BasePlugin.on_unload()` is called
- **THEN** it SHALL call `await self._command_registry.unregister_commands()`
- **AND** the CommandRegistry SHALL remove all registered commands

### Requirement: BasePlugin Event Listener Registration
BasePlugin SHALL automatically register event listeners decorated with _event_listener attribute.

#### Scenario: Register event listeners on load
- **WHEN** `BasePlugin._register_event_listeners()` is called
- **THEN** it SHALL scan all attributes of the plugin for methods with `_event_listener` attribute
- **AND** SHALL call `self.events.add_listener(event_name, attr)` for each
- **AND** SHALL store the (event_name, listener) tuple in `_event_listeners`

#### Scenario: Unregister event listeners on unload
- **WHEN** `BasePlugin._unregister_event_listeners()` is called
- **THEN** it SHALL call `self.events.remove_listener(event_name, listener)` for each stored listener
- **AND** SHALL clear the `_event_listeners` list

### Requirement: BasePlugin Web Panel Registration
BasePlugin SHALL automatically register web panels for plugins implementing WebPanelMixin.

#### Scenario: Register web panel for WebPanelMixin
- **WHEN** `BasePlugin._register_web_panel()` is called and the plugin is an instance of WebPanelMixin
- **THEN** it SHALL call `self.web_panel.register_plugin_panel(self.name, self)` if web_panel exists
- **AND** SHALL log the registration

#### Scenario: Unregister web panel on unload
- **WHEN** `BasePlugin._unregister_web_panel()` is called and the plugin is an instance of WebPanelMixin
- **THEN** it SHALL call `self.web_panel.unregister_plugin_panel(self.name)` if web_panel exists
- **AND** SHALL log the unregistration

### Requirement: BasePlugin Helper Methods
BasePlugin SHALL provide helper methods for common operations like embeds, responses, settings, and logging.

#### Scenario: Create embed with default styling
- **WHEN** `create_embed(title, description, color)` is called
- **THEN** it SHALL return a hikari.Embed with the specified title, description, and color
- **AND** the default color SHALL be hikari.Color(0x7289DA)

#### Scenario: Smart respond handles ephemeral flags
- **WHEN** `smart_respond(ctx, content, embed, ephemeral=True)` is called with an InteractionContext
- **THEN** it SHALL set flags=hikari.MessageFlag.EPHEMERAL
- **AND** SHALL call `ctx.respond()` with the content and embed
- **AND** for prefix contexts, the ephemeral flag SHALL be ignored

#### Scenario: Log command usage with database persistence
- **WHEN** `log_command_usage(ctx, command_name, success, error_message, execution_time)` is called
- **THEN** it SHALL ensure User and Guild records exist in the database
- **AND** SHALL create a CommandUsage record with the provided data
- **AND** SHALL commit the record to the database

#### Scenario: Get and set plugin settings
- **WHEN** `get_setting(guild_id, key, default)` is called
- **THEN** it SHALL query the PluginSetting table for the guild and plugin
- **AND** SHALL return the value for the key or the default if not found
- **WHEN** `set_setting(guild_id, key, value)` is called
- **THEN** it SHALL update or create a PluginSetting record with the key-value pair
- **AND** SHALL commit the change to the database

#### Scenario: Enable/disable plugin in guild
- **WHEN** `enable_in_guild(guild_id)` is called
- **THEN** it SHALL call `set_setting(guild_id, "enabled", True)`
- **WHEN** `disable_in_guild(guild_id)` is called
- **THEN** it SHALL call `set_setting(guild_id, "enabled", False)`
- **AND** `is_enabled_in_guild(guild_id)` SHALL return the boolean value of the "enabled" setting

### Requirement: DatabaseMixin Model Registration
DatabaseMixin SHALL allow plugins to register SQLAlchemy models for automatic table creation.

#### Scenario: Register single model
- **WHEN** `register_model(model_class)` is called with a SQLAlchemy model class
- **THEN** it SHALL validate that the class inherits from DeclarativeBase
- **AND** SHALL validate that the class defines `__tablename__`
- **AND** SHALL add the class to `_plugin_models`
- **AND** SHALL log the registration

#### Scenario: Register multiple models
- **WHEN** `register_models(model_class1, model_class2, ...)` is called
- **THEN** it SHALL call `register_model()` for each model class

#### Scenario: Register models with database manager on load
- **WHEN** `DatabaseMixin.on_load()` is called
- **THEN** it SHALL call `self.db.register_plugin_model(model_class, self.name)` for each model in `_plugin_models`
- **AND** SHALL then call `super().on_load()`

#### Scenario: Unregister models on unload
- **WHEN** `DatabaseMixin.on_unload()` is called
- **THEN** it SHALL call `self.db.unregister_plugin_model(model_class, self.name)` for each model
- **AND** SHALL then call `super().on_unload()`

#### Scenario: Reject invalid model class
- **WHEN** `register_model()` is called with a class that does not inherit from DeclarativeBase
- **THEN** it SHALL raise a ValueError
- **WHEN** `register_model()` is called with a class that does not define `__tablename__`
- **THEN** it SHALL raise a ValueError
