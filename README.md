# Discord Bot Framework

A modular Discord bot built with the Hikari framework, featuring a plugin system, RBAC permissions, hot reload, and database support.

## Features

- 🔌 **Plugin System** - Modular architecture with hot reload support
- 🔒 **RBAC Permissions** - Role-based access control using Discord roles
- 🗄️ **Database Support** - SQLite for development, PostgreSQL for production
- 🐳 **Docker Ready** - Development and production Docker configurations
- 🔄 **Hot Reload** - Automatic plugin reloading during development
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
python -m bot --dev  # Development mode with hot reload
# or
python -m bot.cli run --dev
```

### Docker Development

```bash
# Development with hot reload
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
│   ├── admin/            # Admin commands
│   ├── moderation/       # Moderation commands
│   ├── fun/              # Fun commands and games
│   ├── utility/          # Utility commands
│   └── music/            # Music bot functionality
├── config/               # Configuration management
└── tests/                # Test suite
```

## Creating Plugins

### Basic Plugin Structure

```python
# plugins/myplugin/__init__.py
from .myplugin import MyPlugin

PLUGIN_METADATA = {
    "name": "MyPlugin",
    "version": "1.0.0",
    "author": "Your Name",
    "description": "My awesome plugin",
    "dependencies": [],
    "permissions": ["myplugin.use"],
}

def setup(bot):
    return MyPlugin(bot)
```

```python
# plugins/myplugin/myplugin.py
import hikari
import arc
from bot.plugins.base import BasePlugin
from bot.permissions import requires_permission

class MyPlugin(BasePlugin):
    @property
    def metadata(self):
        return {
            "name": "MyPlugin",
            "version": "1.0.0",
            "description": "My awesome plugin",
        }

    @arc.slash_command(name="hello", description="Say hello")
    @requires_permission("myplugin.use")
    async def hello_command(self, ctx: arc.GatewayContext):
        embed = self.create_embed(
            title="Hello!",
            description="Hello from my plugin!",
            color=hikari.Color(0x00FF00)
        )
        await ctx.respond(embed=embed)
```

### Plugin Features

- **Slash Commands**: Use `@arc.slash_command()` decorator
- **Permissions**: Use `@requires_permission()` for RBAC
- **Settings**: Per-guild plugin configuration
- **Events**: Listen to Discord and bot events
- **Database**: Built-in database access
- **Logging**: Automatic command usage tracking

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
- **Utility**: `utility.info`, `utility.stats` *(available by default)*
- **Music**: `music.play`, `music.queue` *(available by default)*, `music.skip`, `music.volume`

### Managing Permissions

```bash
# Grant permission to a role
/permission grant @Moderator moderation.kick

# Revoke permission from a role
/permission revoke @Moderator moderation.kick

# List permissions for a role
/permission list @Moderator

# List all available permissions
/permission list
```

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
- Hot reload settings
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

### Hot Reload

In development mode, the bot automatically reloads plugins when files change:

```bash
python -m bot --dev
```

### Plugin Development

1. Create plugin directory in `plugins/`
2. Add `__init__.py` with metadata
3. Implement plugin class extending `BasePlugin`
4. Test with hot reload enabled

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

### Admin Plugin
- `/reload` - Reload plugins
- `/plugins` - List loaded plugins
- `/permission` - Manage permissions
- `/bot-info` - Bot information

### Moderation Plugin
- `/kick` - Kick members
- `/ban` - Ban users
- `/timeout` - Timeout members
- `/purge` - Delete messages

### Fun Plugin
- `/roll` - Roll dice
- `/coinflip` - Flip a coin
- `/8ball` - Magic 8-ball
- `/joke` - Random jokes
- `/choose` - Choose from options

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