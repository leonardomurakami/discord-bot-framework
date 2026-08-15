## Purpose
Provides a unified command system that creates both slash and prefix commands from a single decorator definition, with shared argument parsing, permission enforcement, and dual invocation compatibility.

## Requirements

### Requirement: Unified Command Decorator
The command decorator SHALL create metadata for both slash and prefix commands from a single function definition.

#### Scenario: Create unified command metadata
- **WHEN** the `@command(name, description, aliases, permission_node, slash_only, prefix_only, arguments)` decorator is applied to a function
- **THEN** the function SHALL have `_unified_command` attribute with name, description, permission_node, slash_only, prefix_only, arguments, and lightbulb_kwargs
- **AND** if not slash_only, the function SHALL have `_prefix_command` attribute with name, description, aliases, permission_node, and arguments

#### Scenario: Create slash-only command
- **WHEN** the decorator is called with `slash_only=True`
- **THEN** the function SHALL have `_unified_command` attribute
- **AND** the function SHALL NOT have `_prefix_command` attribute

#### Scenario: Create prefix-only command
- **WHEN** the decorator is called with `prefix_only=True`
- **THEN** the function SHALL have `_unified_command` attribute with prefix_only=True
- **AND** the function SHALL NOT have `_prefix_command` attribute

### Requirement: CommandArgument Definition
CommandArgument SHALL define command arguments using hikari OptionType with validation and defaults.

#### Scenario: Define required argument
- **WHEN** `CommandArgument(name, arg_type, description, required=True)` is created
- **THEN** the argument SHALL have the specified name, arg_type, description, and required=True
- **AND** default SHALL be None

#### Scenario: Define optional argument with default
- **WHEN** `CommandArgument(name, arg_type, description, required=False, default=value)` is created
- **THEN** the argument SHALL have required=False and the specified default
- **AND** if default is None, __post_init__ SHALL set type-appropriate defaults ("" for STRING, 0 for INTEGER, False for BOOLEAN, None for others)

#### Scenario: Define argument with choices
- **WHEN** `CommandArgument(name, arg_type, description, choices=[...])` is created
- **THEN** the argument SHALL have the choices list stored

### Requirement: CommandRegistry Slash Command Registration
CommandRegistry SHALL dynamically generate Lightbulb SlashCommand classes for slash commands.

#### Scenario: Register slash command with arguments
- **WHEN** `_register_slash_commands()` finds a method with `_unified_command` attribute and not prefix_only
- **THEN** it SHALL create a dynamic SlashCommand subclass with the command name and description
- **AND** SHALL create an invoke wrapper that extracts arguments from ctx.options
- **AND** SHALL add option descriptors using OptionDescriptorFactory for each argument
- **AND** SHALL register the command class with `self.bot.command_client.register()`
- **AND** SHALL store the original method in `_commands`

#### Scenario: Apply permission decorator to slash command
- **WHEN** the command metadata includes a permission_node
- **THEN** the invoke method SHALL be wrapped with `requires_permission(permission_node)`

#### Scenario: Skip prefix-only commands
- **WHEN** a method has `_unified_command` with prefix_only=True
- **THEN** `_register_slash_commands()` SHALL skip registering it as a slash command

#### Scenario: Handle slash command registration errors
- **WHEN** an exception occurs during slash command registration
- **THEN** the error SHALL be logged and the command SHALL NOT be registered

### Requirement: CommandRegistry Prefix Command Registration
CommandRegistry SHALL register prefix commands with the message handler using PrefixCommand wrapping.

#### Scenario: Register prefix command with arguments
- **WHEN** `_register_prefix_commands()` finds a method with `_prefix_command` attribute
- **THEN** it SHALL create a PrefixCommand instance with name, callback, description, aliases, permission_node, plugin_name, and arguments
- **AND** the callback SHALL be wrapped with `_create_prefix_wrapper()` for argument parsing
- **AND** SHALL call `self.bot.message_handler.add_command(prefix_cmd)`
- **AND** SHALL store the original method in `_commands`

#### Scenario: Apply permission decorator to prefix command
- **WHEN** the prefix command metadata includes a permission_node
- **THEN** the prefix wrapper SHALL wrap the callback with `requires_permission(permission_node)`

#### Scenario: Handle prefix command registration errors
- **WHEN** an exception occurs during prefix command registration
- **THEN** the error SHALL be logged and the command SHALL NOT be registered

### Requirement: CommandRegistry Unregistration
CommandRegistry SHALL unregister all commands when a plugin is unloaded.

#### Scenario: Unregister slash commands
- **WHEN** `unregister_commands()` is called
- **THEN** for each command with `_unified_command` attribute
- **AND** Lightbulb commands SHALL be cleaned up on plugin unload (logged)
- **AND** the command SHALL be removed from `_commands`

#### Scenario: Unregister prefix commands
- **WHEN** `unregister_commands()` is called
- **THEN** for each command with `_prefix_command` attribute
- **AND** it SHALL call `self.bot.message_handler.remove_command(name)`
- **AND** the removal SHALL be logged

#### Scenario: Clear commands list
- **WHEN** `unregister_commands()` completes
- **THEN** `_commands` SHALL be cleared

### Requirement: OptionDescriptorFactory
OptionDescriptorFactory SHALL create appropriate lightbulb option descriptors for CommandArgument definitions.

#### Scenario: Create string option with choices
- **WHEN** `create()` is called with a CommandArgument with arg_type=STRING and choices
- **THEN** it SHALL return `lightbulb.string(name, description, choices=choices, default=default if not required)`

#### Scenario: Create integer option with choices
- **WHEN** `create()` is called with a CommandArgument with arg_type=INTEGER and choices
- **THEN** it SHALL return `lightbulb.integer(name, description, choices=choices, default=default if not required)`

#### Scenario: Create boolean option
- **WHEN** `create()` is called with a CommandArgument with arg_type=BOOLEAN
- **THEN** it SHALL return `lightbulb.boolean(name, description, default=default if not required)`
- **AND** choices SHALL NOT be included (boolean does not support choices)

#### Scenario: Create user option without choices
- **WHEN** `create()` is called with a CommandArgument with arg_type=USER
- **THEN** it SHALL return `lightbulb.user(name, description, default=default if not required)`
- **AND** choices SHALL NOT be included (user does not support choices)

#### Scenario: Create channel option without choices
- **WHEN** `create()` is called with a CommandArgument with arg_type=CHANNEL
- **THEN** it SHALL return `lightbulb.channel(name, description, default=default if not required)`
- **AND** choices SHALL NOT be included (channel does not support choices)

#### Scenario: Create role option without choices
- **WHEN** `create()` is called with a CommandArgument with arg_type=ROLE
- **THEN** it SHALL return `lightbulb.role(name, description, default=default if not required)`
- **AND** choices SHALL NOT be included (role does not support choices)

#### Scenario: Create mentionable option without choices
- **WHEN** `create()` is called with a CommandArgument with arg_type=MENTIONABLE
- **THEN** it SHALL return `lightbulb.mentionable(name, description, default=default if not required)`
- **AND** choices SHALL NOT be included (mentionable does not support choices)

#### Scenario: Create attachment option
- **WHEN** `create()` is called with a CommandArgument with arg_type=ATTACHMENT
- **THEN** it SHALL return `lightbulb.attachment(name, description, default=default if not required)`
- **AND** choices SHALL NOT be included (attachment does not support choices)

### Requirement: ArgumentParserFactory
ArgumentParserFactory SHALL parse prefix command arguments based on their CommandArgument definitions.

#### Scenario: Parse string argument
- **WHEN** `parse_arguments()` is called with a STRING argument definition
- **THEN** StringArgumentParser SHALL return the argument string unchanged
- **AND** if it's the last string argument, it SHALL consume all remaining text

#### Scenario: Parse integer argument
- **WHEN** `parse_arguments()` is called with an INTEGER argument definition
- **THEN** IntegerArgumentParser SHALL attempt to convert the string to int
- **AND** on ValueError, it SHALL return the argument's default value

#### Scenario: Parse boolean argument
- **WHEN** `parse_arguments()` is called with a BOOLEAN argument definition
- **THEN** BooleanArgumentParser SHALL return True if the string is "true", "1", "yes", "on", or "y" (case-insensitive)
- **AND** SHALL return False otherwise

#### Scenario: Parse user argument
- **WHEN** `parse_arguments()` is called with a USER argument definition
- **THEN** UserArgumentParser SHALL strip mention formatting from the string and attempt to parse as user ID
- **AND** SHALL fetch the user via REST API if valid ID
- **AND** on failure, SHALL try to find by username/display_name in cache or via REST API
- **AND** on all failures, SHALL return the argument's default value

#### Scenario: Parse channel argument
- **WHEN** `parse_arguments()` is called with a CHANNEL argument definition
- **THEN** ChannelArgumentParser SHALL strip channel mention formatting and attempt to parse as channel ID
- **AND** SHALL fetch the channel from cache or REST API if valid ID
- **AND** on failure, SHALL try to find by name in cache or via REST API
- **AND** on all failures, SHALL return the argument's default value

#### Scenario: Parse role argument
- **WHEN** `parse_arguments()` is called with a ROLE argument definition
- **THEN** RoleArgumentParser SHALL strip role mention formatting and attempt to parse as role ID
- **AND** SHALL fetch the role from cache or REST API if valid ID
- **AND** on failure, SHALL try to find by name in cache or via REST API
- **AND** on all failures, SHALL return the argument's default value

#### Scenario: Parse mentionable argument
- **WHEN** `parse_arguments()` is called with a MENTIONABLE argument definition
- **THEN** MentionableArgumentParser SHALL try user parsing if the string starts with a user mention
- **AND** SHALL try role parsing if the string starts with a role mention
- **AND** SHALL return the argument's default value if neither succeeds

#### Scenario: Handle missing optional arguments
- **WHEN** `parse_arguments()` is called with fewer args than command_args
- **THEN** for missing optional arguments, the parsed value SHALL be the argument's default
- **AND** for missing required arguments, the parsed value SHALL be None

#### Scenario: Handle parsing errors
- **WHEN** an exception occurs during argument parsing
- **THEN** the error SHALL be logged
- **AND** the parsed value SHALL be the argument's default if not required, or None if required

### Requirement: Dual Slash and Prefix Invocation
Commands defined with the unified decorator SHALL be invocable via both slash and prefix (unless restricted).

#### Scenario: Invoke command via slash
- **WHEN** a user invokes a slash command registered by CommandRegistry
- **THEN** the Lightbulb invoke wrapper SHALL extract arguments from ctx.options
- **AND** SHALL call the original plugin method with the parsed arguments as keyword arguments

#### Scenario: Invoke command via prefix
- **WHEN** a user invokes a prefix command registered by CommandRegistry
- **THEN** the MessageHandler SHALL create a PrefixContext
- **AND** the prefix wrapper SHALL parse arguments using ArgumentParserFactory
- **AND** SHALL call the original plugin method with the parsed arguments as keyword arguments

#### Scenario: Command with aliases works via prefix
- **WHEN** a command is defined with aliases in the decorator
- **THEN** the PrefixCommand SHALL have the aliases list
- **AND** the MessageHandler SHALL recognize the command by any of its aliases

#### Scenario: Slash-only command not available via prefix
- **WHEN** a command is defined with slash_only=True
- **THEN** the function SHALL NOT have a `_prefix_command` attribute
- **AND** the command SHALL NOT be registered with the MessageHandler

#### Scenario: Prefix-only command not available via slash
- **WHEN** a command is defined with prefix_only=True
- **THEN** `_register_slash_commands()` SHALL skip the command
- **AND** the command SHALL NOT be registered with Lightbulb
