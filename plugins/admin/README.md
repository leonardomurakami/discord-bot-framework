# Admin Plugin

Administrative commands for bot management including permissions, server info, and uptime monitoring.

## Overview

The Admin plugin provides essential administrative tools for server owners and bot administrators. It includes commands for managing permissions, viewing bot and server information, and monitoring system status.

## Commands

### Permission Management

#### `!permission` (Alias: `/permission`)
Manage role permissions for the bot's command system.

**Permission Required:** `admin.permissions`

**Usage:**
- `!permission` - List all available permissions
- Lists permissions granted to roles and provides permission management interface

**Features:**
- View all available permissions in the bot
- See which permissions are granted to specific roles
- Interactive permission management system

### Bot Information

#### `!bot-info` (Aliases: `!info`, `/bot-info`)
Display comprehensive bot information and statistics.

**Usage:** `!bot-info`

**Information Displayed:**
- Number of guilds the bot is in
- Number of loaded plugins
- Database connection status
- Bot creation date
- Bot avatar and display information

### Server Information

#### `!server-info` (Aliases: `!serverinfo`, `!guild-info`, `/server-info`)
Display detailed server information and statistics.

**Usage:** `!server-info`

**Information Displayed:**
- Server ID and creation date
- Server owner information
- Member, channel, role, and emoji counts
- Channel breakdown (text/voice/category)
- Server features (Community, Verified, Partnered, etc.)
- Server icon and banner (if available)

### System Monitoring

#### `!uptime` (Aliases: `!up`, `!status`, `/uptime`)
Display bot uptime and system information.

**Usage:** `!uptime`

**Information Displayed:**
- Bot uptime (days, hours, minutes, seconds)
- Bot start time
- Current timestamp
- Memory usage (if psutil is available)
- CPU usage (if psutil is available)
- System uptime (if psutil is available)
- Number of servers
- Bot latency/ping
- Process ID

## Permissions

The Admin plugin defines the following permission nodes:

- `admin.config` - General administrative configuration
- `admin.plugins` - Plugin management operations
- `admin.permissions` - Permission system management

## Dependencies

### Optional Dependencies
- `psutil` - For detailed system information in the uptime command. If not installed, basic uptime information will still be displayed.

## Installation Notes

This plugin is typically essential for bot administration and should be loaded by default. The permission system requires database access to function properly.

## Error Handling

All commands include comprehensive error handling:
- Permission validation
- Database connectivity checks
- Graceful degradation when optional dependencies are unavailable
- User-friendly error messages for common issues

## Security Considerations

- Permission management commands are restricted to users with appropriate permissions
- Sensitive system information is only shown to authorized users
- All administrative actions are logged for audit purposes
