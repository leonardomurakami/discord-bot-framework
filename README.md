# Discord Bot Framework

A modular Discord bot built with the Hikari framework, featuring a plugin system, RBAC permissions, and database support.

## Features

- 🔌 **Plugin System** - Modular architecture with dynamic plugin loading
- 🔒 **RBAC Permissions** - Role-based access control using Discord roles
- 🗄️ **Database Support** - SQLite for development, PostgreSQL for production
- 🐳 **Docker Ready** - Development and production Docker configurations
- 📊 **Analytics & Logging** - Built-in middleware for tracking and monitoring
- ⚡ **Fast Setup** - Get started quickly with uv package management

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for dependency management
- Discord Bot Token

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd discord-bot
```

2. Install dependencies:
```bash
uv pip install -e .
```

3. Copy environment file and configure:
```bash
cp .env.example .env
# Edit .env with your Discord bot token
```

4. Initialize the database:
```bash
python -m bot.cli db create
```

5. Run the bot:
```bash
python -m bot.cli run --dev  # Development mode with development defaults
# or
python -m bot.cli run        # Production mode
```

### Docker Development

```bash
# Development environment
docker-compose up bot-dev

# Production with PostgreSQL
docker-compose --profile production up
```

## Project Structure

```
discord-bot/
├── bot/                    # Core bot framework
│   ├── core/              # Bot core (plugin loader, event system)
│   ├── database/          # Database models and manager
│   ├── permissions/       # RBAC permission system
│   ├── plugins/           # Base plugin classes
│   └── middleware/        # Event middleware
├── plugins/               # Plugin implementations
│   ├── admin/             # Admin commands
│   ├── moderation/        # Moderation commands
│   ├── fun/               # Fun commands and games
│   ├── utility/           # Utility commands
│   ├── help/              # Help commands
│   └── music/             # Music bot functionality
├── config/                # Configuration management
└── tests/                 # Test suite
```

## Creating Plugins

### Basic Plugin Structure

```python
# plugins/myplugin/__init__.py
from .myplugin import MyPlugin

PLUGIN_METADATA = {
    "name": "My Plugin",
    "version": "1.0.0",
    "author": "Your Name",
    "description": "My awesome plugin",
    "permissions": ["myplugin.use"],
}

__all__ = ["MyPlugin"]
```

```python
# plugins/myplugin/myplugin.py
import logging
import hikari
import lightbulb
from bot.plugins.base import BasePlugin
from bot.plugins.commands import command, CommandArgument

logger = logging.getLogger(__name__)

class MyPlugin(BasePlugin):
    def __init__(self, bot) -> None:
        super().__init__(bot)

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
        permission_node="myplugin.use"
    )
    async def hello_command(self, ctx) -> None:
        embed = self.create_embed(
            title="👋 Hello!",
            description=f"Hello, {ctx.author.mention}!",
            color=hikari.Color(0x00FF00)
        )
        await ctx.respond(embed=embed)

    @command(
        name="greet",
        description="Greet a specific user",
        arguments=[
            CommandArgument("user", hikari.OptionType.USER, "User to greet"),
            CommandArgument("message", hikari.OptionType.STRING, "Custom message", required=False)
        ],
        permission_node="myplugin.use"
    )
    async def greet_command(self, ctx, user: hikari.User, message: str = "Hello") -> None:
        embed = self.create_embed(
            title="👋 Greetings!",
            description=f"{message}, {user.mention}!",
            color=hikari.Color(0x5865F2)
        )
        await ctx.respond(embed=embed)
```

### Plugin Features

- **Commands**: Use `@command()` decorator with support for arguments and permissions
- **Lifecycle Management**: `on_load()` and `on_unload()` methods for initialization and cleanup
- **Permissions**: Built-in RBAC with `permission_node` parameter
- **Event Handling**: Listen to Discord events using Hikari event system
- **Database Access**: Built-in database manager for data persistence
- **Utilities**: Helper methods for embeds, responses, and command logging
- **Error Handling**: Comprehensive error handling and logging support

## Permission System

The bot uses a role-based access control (RBAC) system with automatic hierarchy:

### Permission Hierarchy

1. **Server Owner**: Has all permissions automatically
2. **Administrator Role**: Users with Discord's Administrator permission have all bot permissions
3. **Admin Permissions**: `admin.*` permissions grant all other permissions
4. **Moderation Permissions**: `moderation.*` permissions grant `utility.*` and `fun.*` permissions
5. **Default Permissions**: Basic commands available to everyone

### Built-in Permissions

- **Admin**: `admin.config`, `admin.plugins`, `admin.permissions`
- **Moderation**: `moderation.kick`, `moderation.ban`, `moderation.mute`, `moderation.timeout`, `moderation.purge`
- **Fun**: `fun.games`, `fun.images` *(available by default)*
- **Utility**: Basic utility commands *(available by default)*
- **Music**: `music.play`, `music.manage`, `music.settings`

### Managing Permissions

Use the `/permission` command in Discord to manage role permissions:

- Grant permissions to roles
- Revoke permissions from roles
- List permissions for specific roles
- View all available permissions

See the Admin Plugin documentation for detailed usage examples.

## Configuration

### Environment Variables

```env
DISCORD_TOKEN=your_discord_bot_token
DATABASE_URL=sqlite:///data/bot.db
BOT_PREFIX=!
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Bot Settings

Edit `config/settings.py` to customize:

- Enabled plugins
- Plugin directories
- Database configuration

## Database

### Models

The bot includes these database models:

- **Guild**: Server settings and configuration
- **User**: User data and preferences
- **GuildUser**: Per-server user data
- **Permission**: Available permissions
- **RolePermission**: Role-permission mappings
- **CommandUsage**: Command usage analytics
- **PluginSetting**: Per-plugin, per-guild settings

### Commands

```bash
# Create database tables
python -m bot.cli db create

# Reset database (WARNING: deletes all data)
python -m bot.cli db reset
```

## Development

### Plugin Development

1. Create plugin directory in `plugins/`
2. Add `__init__.py` with metadata
3. Implement plugin class extending `BasePlugin`

### Adding Dependencies

```bash
# Add runtime dependency
uv add package-name

# Add development dependency
uv add --dev package-name

# Add optional dependency (e.g., music features)
uv add --optional music package-name
```

## Production Deployment

### Docker

```bash
# Build production image
docker build --target production -t discord-bot .

# Run with docker-compose
docker-compose --profile production up -d
```

### Environment Setup

1. Use PostgreSQL database
2. Set `ENVIRONMENT=production`
3. Configure proper logging
4. Set up monitoring/alerting
5. Use secrets management for tokens

## Available Plugins

The bot includes several built-in plugins with various functionality:

- **Admin Plugin**: Bot management, permissions, server information
- **Moderation Plugin**: Member management, message moderation, timeouts
- **Fun Plugin**: Games, entertainment commands, random utilities
- **Utility Plugin**: User info, timestamps, encoding utilities
- **Help Plugin**: Command help and plugin information
- **Music Plugin**: Full-featured music bot with queue management

Each plugin has its own README with detailed command documentation. See the `plugins/` directory for specific plugin documentation.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure code passes linting
5. Submit a pull request

## License

[MIT License](LICENSE)

## Support

- Create an issue for bugs or feature requests
- Check the wiki for detailed documentation
- Join our Discord server for community support