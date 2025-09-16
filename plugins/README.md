# Plugin Development Guide

This guide explains how to create, structure, and develop plugins for the Discord bot framework.

## Table of Contents
- [Plugin Structure](#plugin-structure)
- [Creating a New Plugin](#creating-a-new-plugin)
- [Plugin Metadata](#plugin-metadata)
- [Base Plugin Class](#base-plugin-class)
- [Commands](#commands)
- [Events](#events)
- [Permissions](#permissions)
- [Database Access](#database-access)
- [Utilities](#utilities)
- [Best Practices](#best-practices)
- [Examples](#examples)

## Plugin Structure

Each plugin should be organized as a Python package with the following structure:

```
plugins/
├── your_plugin/
│   ├── __init__.py          # Plugin exports and metadata
│   └── your_plugin.py       # Main plugin implementation
└── README.md               # This guide
```

### Required Files

1. **`__init__.py`** - Contains plugin metadata and exports
2. **`your_plugin.py`** - Main plugin class and commands

## Creating a New Plugin

### 1. Create Plugin Directory
```bash
mkdir plugins/my_plugin
```

### 2. Create `__init__.py`
```python
from .my_plugin import MyPlugin

PLUGIN_METADATA = {
    "name": "My Plugin",
    "version": "1.0.0",
    "author": "Your Name",
    "description": "Description of what your plugin does",
    "permissions": ["my_plugin.command1", "my_plugin.command2"],
}

__all__ = ["MyPlugin"]
```

### 3. Create `my_plugin.py`
```python
import logging
import hikari
import lightbulb

from bot.plugins.base import BasePlugin
from bot.plugins.commands import command, CommandArgument

logger = logging.getLogger(__name__)


class MyPlugin(BasePlugin):
    def __init__(self, bot) -> None:
        super().__init__(bot)
        # Initialize plugin-specific attributes here

    async def on_load(self) -> None:
        """Called when the plugin is loaded."""
        await super().on_load()
        logger.info("MyPlugin loaded successfully")

    async def on_unload(self) -> None:
        """Called when the plugin is unloaded."""
        await super().on_unload()
        logger.info("MyPlugin unloaded")

    @command(
        name="hello",
        description="Say hello to the user",
        aliases=["hi", "greet"]
    )
    async def hello_command(self, ctx) -> None:
        embed = self.create_embed(
            title="👋 Hello!",
            description=f"Hello, {ctx.author.mention}!",
            color=hikari.Color(0x00FF00)
        )
        await ctx.respond(embed=embed)
```

## Plugin Metadata

Metadata is defined in the `__init__.py` file as a `PLUGIN_METADATA` dictionary:

```python
PLUGIN_METADATA = {
    "name": "Display Name",           # Plugin display name
    "version": "1.0.0",              # Semantic version
    "author": "Author Name",         # Plugin author
    "description": "Plugin purpose", # Brief description
    "permissions": [                 # List of permission nodes
        "plugin.permission1",
        "plugin.permission2"
    ],
}
```

### Metadata Fields
- **`name`** (required) - Display name shown in help and plugin lists
- **`version`** (required) - Plugin version following semantic versioning
- **`author`** (required) - Plugin author/maintainer
- **`description`** (required) - Brief description of plugin functionality
- **`permissions`** (optional) - List of permission nodes the plugin uses

## Base Plugin Class

All plugins inherit from `BasePlugin` which provides common functionality:

### Available Properties
```python
self.bot           # Main bot instance
self.logger        # Plugin-specific logger
```

### Available Methods

#### Lifecycle Methods
```python
async def on_load(self) -> None:
    """Called when plugin is loaded. Override for initialization."""

async def on_unload(self) -> None:
    """Called when plugin is unloaded. Override for cleanup."""
```

#### Utility Methods
```python
def create_embed(self, title: str = None, description: str = None,
                color: hikari.Color = None) -> hikari.Embed:
    """Create a standardized embed with optional parameters."""

async def smart_respond(self, ctx, content: str = None, *,
                       embed: hikari.Embed = None, ephemeral: bool = False) -> None:
    """Smart response that handles different context types."""

async def log_command_usage(self, ctx, command_name: str,
                           success: bool, error: str = None) -> None:
    """Log command usage for analytics and debugging."""
```

#### Bot Access
```python
self.bot.hikari_bot          # Hikari gateway bot instance
self.bot.db                  # Database manager
self.bot.permission_manager  # Permission system
self.bot.plugin_loader       # Plugin loader
self.bot.event_system        # Event system
```

## Commands

Commands are defined using the `@command` decorator:

### Basic Command
```python
@command(
    name="basic",
    description="A basic command"
)
async def basic_command(self, ctx) -> None:
    await ctx.respond("Hello!")
```

### Command with Arguments
```python
@command(
    name="greet",
    description="Greet a user",
    arguments=[
        CommandArgument("user", hikari.OptionType.USER, "User to greet"),
        CommandArgument("message", hikari.OptionType.STRING, "Custom message", required=False)
    ]
)
async def greet_command(self, ctx, user: hikari.User, message: str = "Hello!") -> None:
    await ctx.respond(f"{message} {user.mention}!")
```

### Command with Permissions
```python
@command(
    name="admin",
    description="Admin-only command",
    permission_node="my_plugin.admin"
)
async def admin_command(self, ctx) -> None:
    await ctx.respond("Admin command executed!")
```

### Command Options
- **`name`** (required) - Command name
- **`description`** (required) - Command description
- **`aliases`** (optional) - List of command aliases
- **`permission_node`** (optional) - Required permission
- **`arguments`** (optional) - List of command arguments

### Argument Types
Available argument types from `hikari.OptionType`:
- `STRING` - Text input
- `INTEGER` - Whole numbers
- `USER` - Discord user
- `CHANNEL` - Discord channel
- `ROLE` - Discord role
- `BOOLEAN` - True/false

## Events

Plugins can listen to Discord events by defining event handlers:

### Event Handler Example
```python
@self.bot.hikari_bot.listen(hikari.GuildMessageCreateEvent)
async def on_message(self, event: hikari.GuildMessageCreateEvent) -> None:
    """Handle message creation events."""
    if event.author.is_bot:
        return

    # Process message
    if "hello" in event.content.lower():
        await event.message.respond("Hello there!")
```

### Common Events
- `hikari.GuildMessageCreateEvent` - New messages
- `hikari.MemberCreateEvent` - Members joining
- `hikari.MemberDeleteEvent` - Members leaving
- `hikari.ReactionAddEvent` - Reactions added
- `hikari.VoiceStateUpdateEvent` - Voice state changes

## Permissions

The framework includes a permission system for controlling command access:

### Defining Permissions
```python
# In PLUGIN_METADATA
"permissions": [
    "my_plugin.basic",        # Basic permission
    "my_plugin.admin",        # Admin permission
    "my_plugin.moderation"    # Moderation permission
]
```

### Using Permissions
```python
@command(
    name="moderate",
    description="Moderation command",
    permission_node="my_plugin.moderation"
)
async def moderate_command(self, ctx) -> None:
    # Only users with 'my_plugin.moderation' permission can use this
    await ctx.respond("Moderation action performed!")
```

### Permission Naming Convention
Use the format: `plugin_name.permission_type`
- `plugin_name.basic` - Basic functionality
- `plugin_name.admin` - Administrative functions
- `plugin_name.moderate` - Moderation functions

## Database Access

Access the database through the bot instance:

```python
async def get_user_data(self, user_id: int) -> dict:
    """Example database query."""
    async with self.bot.db.acquire() as conn:
        query = "SELECT * FROM users WHERE user_id = $1"
        result = await conn.fetchrow(query, user_id)
        return dict(result) if result else None

async def save_user_data(self, user_id: int, data: dict) -> None:
    """Example database insert/update."""
    async with self.bot.db.acquire() as conn:
        query = """
        INSERT INTO users (user_id, data)
        VALUES ($1, $2)
        ON CONFLICT (user_id)
        DO UPDATE SET data = $2
        """
        await conn.execute(query, user_id, data)
```

## Utilities

### Creating Embeds
```python
# Basic embed
embed = self.create_embed(
    title="Success",
    description="Operation completed successfully!",
    color=hikari.Color(0x00FF00)
)

# Custom embed
embed = hikari.Embed(
    title="Custom Embed",
    description="Description here",
    color=hikari.Color(0x5865F2)
)
embed.add_field("Field Name", "Field Value", inline=True)
embed.set_thumbnail("https://example.com/image.png")
```

### Error Handling
```python
@command(name="example", description="Example with error handling")
async def example_command(self, ctx) -> None:
    try:
        # Command logic here
        result = await some_operation()

        embed = self.create_embed(
            title="✅ Success",
            description=f"Result: {result}",
            color=hikari.Color(0x00FF00)
        )
        await ctx.respond(embed=embed)
        await self.log_command_usage(ctx, "example", True)

    except Exception as e:
        logger.error(f"Error in example command: {e}")

        embed = self.create_embed(
            title="❌ Error",
            description=f"An error occurred: {str(e)}",
            color=hikari.Color(0xFF0000)
        )
        await self.smart_respond(ctx, embed=embed, ephemeral=True)
        await self.log_command_usage(ctx, "example", False, str(e))
```

### HTTP Requests
```python
import aiohttp

class MyPlugin(BasePlugin):
    def __init__(self, bot) -> None:
        super().__init__(bot)
        self.session: aiohttp.ClientSession = None

    async def on_load(self) -> None:
        self.session = aiohttp.ClientSession()
        await super().on_load()

    async def on_unload(self) -> None:
        if self.session:
            await self.session.close()
        await super().on_unload()

    async def fetch_data(self, url: str) -> dict:
        """Example HTTP request."""
        async with self.session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"HTTP {response.status}")
```

## Best Practices

### Code Organization
1. **Keep plugins focused** - One plugin should handle one area of functionality
2. **Use descriptive names** - Commands and functions should be self-explanatory
3. **Handle errors gracefully** - Always use try/except blocks for external operations
4. **Log appropriately** - Use the plugin logger for debugging and error tracking

### Performance
1. **Use async/await** - All database and HTTP operations should be asynchronous
2. **Limit API calls** - Cache data when possible, respect rate limits
3. **Clean up resources** - Close sessions, connections in `on_unload()`

### Security
1. **Validate input** - Always validate user input before processing
2. **Use permissions** - Protect sensitive commands with appropriate permissions
3. **Sanitize output** - Be careful with user-generated content in embeds
4. **No secrets in code** - Use environment variables for API keys

### User Experience
1. **Provide feedback** - Always respond to user commands
2. **Use embeds** - Rich embeds are more visually appealing than plain text
3. **Handle edge cases** - Consider what happens with invalid input
4. **Add helpful aliases** - Provide shorter aliases for commonly used commands

## Examples

### Simple Utility Plugin
```python
# plugins/utils/__init__.py
from .utils import UtilsPlugin

PLUGIN_METADATA = {
    "name": "Utils",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Utility commands for server management",
    "permissions": ["utils.info"],
}

__all__ = ["UtilsPlugin"]
```

```python
# plugins/utils/utils.py
import logging
import hikari
import lightbulb
from datetime import datetime

from bot.plugins.base import BasePlugin
from bot.plugins.commands import command, CommandArgument

logger = logging.getLogger(__name__)


class UtilsPlugin(BasePlugin):
    @command(
        name="serverinfo",
        description="Display server information",
        permission_node="utils.info"
    )
    async def server_info(self, ctx) -> None:
        guild = ctx.get_guild()
        if not guild:
            await ctx.respond("This command can only be used in a server!")
            return

        embed = self.create_embed(
            title=f"🏰 {guild.name}",
            color=hikari.Color(0x5865F2)
        )

        embed.add_field("Members", str(guild.member_count), inline=True)
        embed.add_field("Owner", f"<@{guild.owner_id}>", inline=True)
        embed.add_field("Created", f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)

        if guild.icon_url:
            embed.set_thumbnail(guild.icon_url)

        await ctx.respond(embed=embed)

    @command(
        name="userinfo",
        description="Display user information",
        arguments=[
            CommandArgument("user", hikari.OptionType.USER, "User to check", required=False)
        ]
    )
    async def user_info(self, ctx, user: hikari.User = None) -> None:
        target = user or ctx.author

        embed = self.create_embed(
            title=f"👤 {target.username}",
            color=hikari.Color(0x5865F2)
        )

        embed.add_field("ID", str(target.id), inline=True)
        embed.add_field("Created", f"<t:{int(target.created_at.timestamp())}:R>", inline=True)
        embed.add_field("Bot", "Yes" if target.is_bot else "No", inline=True)

        if target.make_avatar_url():
            embed.set_thumbnail(target.make_avatar_url())

        await ctx.respond(embed=embed)
```

This guide should help you create well-structured, maintainable plugins for the Discord bot framework. For more examples, check the existing plugins in this directory.