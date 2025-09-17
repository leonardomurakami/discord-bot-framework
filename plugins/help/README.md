# Help Plugin

Comprehensive help system showing commands and usage information with interactive plugin exploration.

## Overview

The Help plugin provides an advanced, user-friendly help system for the Discord bot. It features interactive dropdown menus, detailed command information, plugin exploration, and persistent views that survive bot restarts.

## Features

### Interactive Help System
- **Dropdown Navigation:** Browse plugins and commands using interactive dropdown menus
- **Persistent Views:** Help interfaces remain functional even after bot restarts
- **Real-time Updates:** Dynamic content that reflects current bot state
- **Plugin Categories:** Organized browsing by plugin functionality

### Comprehensive Information
- **Command Details:** Usage patterns, aliases, permissions, and descriptions
- **Plugin Overview:** Plugin metadata, version info, and command listings
- **System Statistics:** Bot status, loaded plugins, and server information
- **Search Capabilities:** Find specific commands or plugins quickly

## Commands

### Main Help Commands

#### `!help` (Aliases: `!h`, `/help`)
Show the main help interface with interactive plugin exploration.

**Usage:**
- `!help` - Display general help with plugin dropdown
- `!help <command>` - Get specific help for a command
- `!help <plugin>` - Get detailed information about a plugin

**Features:**
- Interactive dropdown menu for plugin browsing
- General bot overview and statistics
- Essential commands showcase
- Getting started guidance

#### `!commands` (Aliases: `!cmds`, `/commands`)
List all available commands organized by plugin.

**Permission Required:** `help.commands`

**Usage:** `!commands`

**Features:**
- Commands grouped by functionality
- Clean, organized display
- Quick overview of all available commands

#### `!plugins` (Aliases: `!plugin-list`, `/plugins`)
List all loaded plugins with their information.

**Permission Required:** `help.plugins`

**Usage:** `!plugins`

**Information Displayed:**
- Plugin names and versions
- Plugin authors
- Brief descriptions
- Plugin status

## Interactive Components

### Plugin Selection Dropdown
The help system features a sophisticated dropdown menu that allows users to:
- Return to general help overview
- Browse individual plugins
- View detailed command information for each plugin
- Navigate seamlessly between different sections

### Persistent Views
The help system uses persistent views that:
- Survive bot restarts
- Maintain functionality across sessions
- Handle errors gracefully
- Provide consistent user experience

## Information Display

### General Help Overview
- Bot introduction and statistics
- Number of plugins and commands
- Command prefix information
- Essential commands showcase
- Plugin categories overview
- Getting started instructions

### Plugin-Specific Help
- Plugin metadata (name, version, author)
- Detailed command listings with usage patterns
- Command arguments and options
- Permission requirements
- Aliases and shortcuts

### Command-Specific Help
- Detailed usage instructions
- Available aliases
- Required permissions
- Parameter descriptions
- Example usage

## Permissions

The Help plugin defines the following permission nodes:

- `help.commands` - Access to the commands listing command
- `help.plugins` - Access to the plugins listing command

The main help command is available to all users without permission restrictions.

## Technical Features

### Advanced Navigation
- Multi-page support for large command lists
- Field length management for Discord embed limits
- Smart text truncation with continuation indicators
- Context-aware navigation

### Error Handling
- Graceful degradation when plugins are unavailable
- Fallback information for missing metadata
- User-friendly error messages
- Recovery from API failures

### Performance Optimization
- Cached plugin information
- Efficient memory usage
- Minimal API calls
- Fast response times

## Usage Examples

### Basic Help Usage
```
User: !help
Bot: [Interactive help embed with dropdown menu]

User: [Selects "Fun" from dropdown]
Bot: [Updates to show Fun plugin commands with details]
```

### Specific Command Help
```
User: !help roll
Bot: 📖 Help: roll
     Roll dice using standard dice notation
     Usage: !roll
     Aliases: r
     Permission: fun.games
```

### Plugin Exploration
```
User: !help music
Bot: 🔌 Plugin: Music
     Music playback functionality with voice channel support
     Version: 1.0.0
     Author: Bot Framework
     Commands: play, pause, skip, queue, volume...
```

## Integration

The Help plugin integrates deeply with the bot framework:
- **Plugin Loader:** Accesses plugin metadata and registration information
- **Command System:** Retrieves command definitions and usage patterns
- **Permission System:** Displays permission requirements and restrictions
- **Database:** Tracks usage statistics and user interactions

## Customization

The help system can be customized through:
- **Color Schemes:** Adjust embed colors for branding
- **Content Formatting:** Modify information display patterns
- **Navigation Options:** Add or remove dropdown options
- **Permission Levels:** Control access to different help features

## Error Recovery

The plugin includes robust error recovery mechanisms:
- **Plugin Failures:** Graceful handling of unloaded plugins
- **Network Issues:** Offline operation capabilities
- **Permission Errors:** Clear messaging for access restrictions
- **Data Corruption:** Automatic fallbacks and recovery procedures
