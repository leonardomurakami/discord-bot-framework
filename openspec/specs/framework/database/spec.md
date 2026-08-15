## Purpose
Provides an async SQLAlchemy database manager with support for SQLite and PostgreSQL engines, session context management, core and plugin model registration, and table creation.

## Requirements

### Requirement: Async engine selection
The DatabaseManager SHALL automatically select and configure the appropriate async engine based on the database URL scheme.

#### Scenario: Configure SQLite engine
- **WHEN** the database URL starts with `sqlite://`
- **THEN** the manager converts it to `sqlite+aiosqlite://` and configures the engine with `check_same_thread=False`

#### Scenario: Configure PostgreSQL engine
- **WHEN** the database URL starts with `postgresql://`
- **THEN** the manager converts it to `postgresql+asyncpg://` and configures the engine with connection pooling (pool_size=20, max_overflow=30, pool_pre_ping=True, pool_recycle=300)

### Requirement: Session context manager
The DatabaseManager SHALL provide an async context manager for database sessions with automatic commit and rollback.

#### Scenario: Commit successful transaction
- **WHEN** `async with db_manager.session() as session:` is used and no exception occurs
- **THEN** the session is committed and closed when exiting the context

#### Scenario: Rollback on exception
- **WHEN** an exception is raised within the `async with db_manager.session()` context
- **THEN** the session is rolled back, the exception is re-raised, and the session is closed

### Requirement: Core table creation
The DatabaseManager SHALL create tables for core framework models on demand.

#### Scenario: Create core tables
- **WHEN** `create_core_tables()` is called
- **THEN** all tables defined in `Base.metadata` (Guild, User, GuildUser, Permission, RolePermission, UserPermission, CommandUsage, PluginSetting) are created in the database

### Requirement: Plugin model registration
The DatabaseManager SHALL allow plugins to register custom SQLAlchemy models for table creation.

#### Scenario: Register plugin model
- **WHEN** a plugin calls `register_plugin_model(model_class, plugin_name)` with a valid DeclarativeBase subclass
- **THEN** the model is stored in `_plugin_models[plugin_name]` and logged

#### Scenario: Reject invalid model
- **WHEN** `register_plugin_model()` is called with a class that does not inherit from DeclarativeBase
- **THEN** a ValueError is raised

#### Scenario: Reject model without tablename
- **WHEN** `register_plugin_model()` is called with a class lacking `__tablename__`
- **THEN** a ValueError is raised

### Requirement: Plugin table creation
The DatabaseManager SHALL create tables for registered plugin models separately from core tables.

#### Scenario: Create plugin tables
- **WHEN** `create_plugin_tables()` is called and models are registered
- **THEN** tables are created for each registered plugin model using `model_class.metadata.create_all`

### Requirement: Plugin model discovery
The DatabaseManager SHALL provide methods to retrieve registered plugin models by plugin name or globally.

#### Scenario: Get models for specific plugin
- **WHEN** `get_plugin_models(plugin_name)` is called with a registered plugin name
- **THEN** a list of model classes registered for that plugin is returned

#### Scenario: Get all plugin models
- **WHEN** `get_plugin_models()` is called without arguments
- **THEN** a list of all model classes from all registered plugins is returned

### Requirement: Model unregistration
The DatabaseManager SHALL allow plugins to unregister models during unload.

#### Scenario: Unregister plugin model
- **WHEN** `unregister_plugin_model(model_class, plugin_name)` is called
- **THEN** the model is removed from `_plugin_models[plugin_name]` and the plugin entry is deleted if empty

### Requirement: Health check
The DatabaseManager SHALL provide a health check method to verify database connectivity.

#### Scenario: Successful health check
- **WHEN** `health_check()` is called and the database is accessible
- **THEN** the method executes `SELECT 1` and returns True

#### Scenario: Failed health check
- **WHEN** `health_check()` is called and the database is unreachable
- **THEN** the method logs the error and returns False

### Requirement: Database connection cleanup
The DatabaseManager SHALL properly dispose of the database engine on shutdown.

#### Scenario: Close database connection
- **WHEN** `close()` is called
- **THEN** the engine is disposed and the connection is closed

### Requirement: Core model definitions
The framework SHALL define core ORM models for guild configuration, users, permissions, command analytics, and plugin settings.

#### Scenario: Guild model structure
- **WHEN** the Guild model is inspected
- **THEN** it contains fields for id, name, prefix, language, settings (JSON), created_at, updated_at, and relationships to users, role_permissions, user_permissions, command_usage, and plugin_settings

#### Scenario: RolePermission model structure
- **WHEN** the RolePermission model is inspected
- **THEN** it contains fields for id, guild_id, role_id, permission_id, granted, created_at, with a unique constraint on (guild_id, role_id, permission_id) and an index on (guild_id, role_id)

### Requirement: Global database manager instance
The framework SHALL provide a global DatabaseManager singleton for use across the application.

#### Scenario: Access global database manager
- **WHEN** code imports `db_manager` from `bot.database`
- **THEN** a singleton DatabaseManager instance initialized with settings.database_url is returned
