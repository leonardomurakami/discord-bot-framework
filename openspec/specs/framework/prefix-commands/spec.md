## Purpose
Handles text-based commands prefixed with a configurable bot prefix, including command lookup, alias resolution, permission enforcement, and context creation for plugin callbacks.

## Requirements

### Requirement: Bot message filtering
The MessageCommandHandler SHALL ignore messages sent by bot accounts to prevent self-triggering and bot loops.

#### Scenario: Ignore bot message
- **WHEN** `handle_message` receives a GuildMessageCreateEvent where `author.is_bot` is True
- **THEN** the handler SHALL return False without processing the command

### Requirement: DM message filtering
The MessageCommandHandler SHALL only process messages from guild channels, ignoring direct messages.

#### Scenario: Ignore DM message
- **WHEN** `handle_message` receives an event with `guild_id` as None
- **THEN** the handler SHALL return False without processing

### Requirement: Prefix validation
The MessageCommandHandler SHALL only process messages that start with the guild-specific bot prefix.

#### Scenario: Message starts with correct prefix
- **WHEN** a message content starts with the guild prefix returned by `bot.get_guild_prefix(guild_id)`
- **THEN** the handler SHALL proceed to parse the command

#### Scenario: Message lacks prefix
- **WHEN** a message content does not start with the guild prefix
- **THEN** the handler SHALL return False without processing

### Requirement: Command parsing
The MessageCommandHandler SHALL parse the command name and arguments from the message content after stripping the prefix.

#### Scenario: Parse command with arguments
- **WHEN** message content is "!ping hello world" after prefix stripping
- **THEN** command_name SHALL be "ping" and args SHALL be ["hello", "world"]

#### Scenario: Parse command without arguments
- **WHEN** message content is "!ping" after prefix stripping
- **THEN** command_name SHALL be "ping" and args SHALL be an empty list

### Requirement: Command lookup
The MessageCommandHandler SHALL look up commands by name in the registered commands dictionary.

#### Scenario: Command found
- **WHEN** the parsed command_name exists in the commands dict
- **THEN** the corresponding PrefixCommand object SHALL be retrieved for execution

#### Scenario: Command not found
- **WHEN** the parsed command_name does not exist in the commands dict
- **THEN** the handler SHALL return False without processing

### Requirement: Alias resolution
The MessageCommandHandler SHALL support command aliases that map to the same PrefixCommand object.

#### Scenario: Resolve alias to command
- **WHEN** a command is registered with aliases ["p", "ping"] and user types "!p"
- **THEN** the handler SHALL retrieve the same PrefixCommand object as for "!ping"

### Requirement: PrefixContext creation
The MessageCommandHandler SHALL create a PrefixContext object containing event, bot, args, and Discord entity references.

#### Scenario: Context contains event data
- **WHEN** PrefixContext is created with event, bot, and args
- **THEN** the context SHALL expose author, member, guild_id, channel_id, and event properties

#### Scenario: Context provides respond method
- **WHEN** `ctx.respond(content="hello")` is called on PrefixContext
- **THEN** a message SHALL be created via `bot.rest.create_message` with the content

### Requirement: Permission node enforcement
The MessageCommandHandler SHALL check permission nodes before executing commands that require them.

#### Scenario: Permission check passes
- **WHEN** a command has `permission_node="admin.commands"` and the user has that permission
- **THEN** the command callback SHALL be executed

#### Scenario: Permission check fails
- **WHEN** a command has `permission_node="admin.commands"` and the user lacks that permission
- **THEN** the handler SHALL respond with an error message and return True without executing the callback

### Requirement: Permission manager integration
The MessageCommandHandler SHALL integrate with the bot's permission_manager for permission checks when available.

#### Scenario: Permission manager exists
- **WHEN** `bot.permission_manager` is available and command has permission_node
- **THEN** `has_permission(guild_id, member, permission_node)` SHALL be called to validate access

#### Scenario: Permission manager missing
- **WHEN** a command has permission_node but `bot.permission_manager` is not available
- **THEN** the permission check SHALL be skipped and command SHALL execute

### Requirement: Command execution
The MessageCommandHandler SHALL execute the command callback with the PrefixContext as the argument.

#### Scenario: Execute command callback
- **WHEN** command lookup and permission checks succeed
- **THEN** `await command.callback(ctx)` SHALL be called with the PrefixContext

### Requirement: Command error handling
The MessageCommandHandler SHALL catch and log exceptions during command execution and respond to the user with an error message.

#### Scenario: Command callback raises exception
- **WHEN** the command callback raises an exception during execution
- **THEN** the exception SHALL be logged and an error response SHALL be sent to the user

#### Scenario: Error response fails
- **WHEN** sending the error response also raises an exception
- **THEN** the response error SHALL be logged without crashing the handler

### Requirement: Command registration
The MessageCommandHandler SHALL register PrefixCommand objects by name and populate alias mappings.

#### Scenario: Register command with aliases
- **WHEN** `add_command(PrefixCommand(name="ban", aliases=["b", "block"]))` is called
- **THEN** the command SHALL be stored under "ban", "b", and "block" keys in the commands dict

### Requirement: Command removal
The MessageCommandHandler SHALL remove commands and all their aliases from the registry.

#### Scenario: Remove command by name
- **WHEN** `remove_command("ban")` is called for a command with aliases ["b", "block"]
- **THEN** the command SHALL be removed from "ban", "b", and "block" keys in the commands dict

### Requirement: Guild-specific prefix retrieval
The MessageCommandHandler SHALL retrieve guild-specific prefixes from the bot for prefix validation.

#### Scenario: Get guild prefix
- **WHEN** processing a message from guild_id
- **THEN** `bot.get_guild_prefix(guild_id)` SHALL be called to retrieve the prefix for that guild

### Requirement: Case-insensitive command lookup
The MessageCommandHandler SHALL perform case-insensitive command name lookup.

#### Scenario: Lowercase command name
- **WHEN** the message content is "!PING" after prefix stripping
- **THEN** command_name SHALL be converted to "ping" before lookup in the commands dict
