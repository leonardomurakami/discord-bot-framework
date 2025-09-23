# Moderation Plugin

Moderation commands for server management including kick, ban, timeout, slowmode, and message purging.

## Overview

The Moderation plugin provides essential server management tools for moderators and administrators. It includes commands for member discipline, message management, and channel control with comprehensive logging and safety features.

## Commands

### Member Discipline

#### `!kick` (Alias: `/kick`)
Kick a member from the server.

**Permission Required:** `moderation.members.kick`

**Usage:** `!kick <member> [reason]`

**Examples:**
- `!kick @user` - Kick user with no reason
- `!kick @user Spamming in chat` - Kick user with reason

**Features:**
- Attempts to send DM notification before kicking
- Prevents self-targeting and bot-targeting
- Comprehensive error handling for permission issues
- Detailed logging of all kick actions

#### `!ban` (Alias: `/ban`)
Ban a user from the server with message deletion options.

**Permission Required:** `moderation.members.ban`

**Usage:** `!ban <user> [delete_days] [reason]`

**Parameters:**
- `user` - User to ban (can be member or user ID)
- `delete_days` - Days of messages to delete (default: 1, max: 7)
- `reason` - Reason for the ban

**Examples:**
- `!ban @user` - Ban user, delete 1 day of messages
- `!ban @user 7 Repeated violations` - Ban user, delete 7 days of messages
- `!ban 123456789 0 Alt account` - Ban by ID, don't delete messages

**Features:**
- Supports banning users not in the server (by ID)
- Attempts to send DM notification before banning
- Configurable message deletion period
- Prevents self-targeting and bot-targeting

#### `!timeout` (Alias: `/timeout`)
Temporarily timeout a member (Discord timeout feature).

**Permission Required:** `moderation.members.timeout`

**Usage:** `!timeout <member> <duration_minutes> [reason]`

**Parameters:**
- `member` - Member to timeout
- `duration_minutes` - Timeout duration in minutes
- `reason` - Reason for timeout

**Examples:**
- `!timeout @user 10` - Timeout user for 10 minutes
- `!timeout @user 60 Disruptive behavior` - Timeout for 1 hour with reason

**Features:**
- Supports timeout durations up to Discord's maximum
- Smart duration formatting (minutes/hours display)
- Prevents self-targeting and bot-targeting
- Uses Discord's native timeout system

#### `!unban` (Alias: `/unban`)
Remove a ban from a user.

**Permission Required:** `moderation.members.ban`

**Usage:** `!unban <user_id> [reason]`

**Parameters:**
- `user_id` - User ID to unban (accepts user mentions or plain IDs)
- `reason` - Reason for unbanning

**Examples:**
- `!unban 123456789` - Unban user by ID
- `!unban @user Appeal accepted` - Unban with reason

**Features:**
- Validates user is actually banned before attempting unban
- Displays user information when successful
- Comprehensive error handling for invalid IDs

### Message Management

#### `!purge` (Aliases: `!clear`, `/purge`)
Delete multiple messages from a channel.

**Permission Required:** `moderation.channels.purge`

**Usage:** 
- `!purge <amount>` - Delete last N messages
- `!purge <amount> <user>` - Delete N messages from specific user

**Parameters:**
- `amount` - Number of messages to delete (1-100)
- `user` - (Optional) Only delete messages from this user

**Examples:**
- `!purge 10` - Delete last 10 messages
- `!purge 50 @user` - Delete up to 50 messages from specific user

**Features:**
- Supports bulk message deletion (up to 100 messages)
- User-specific message filtering
- Searches through message history for user-specific purges
- Respects Discord's bulk delete limitations

### Channel Management

#### `!slowmode` (Aliases: `!slow`, `/slowmode`)
Set channel slowmode (rate limiting).

**Permission Required:** `moderation.channels.slowmode`

**Usage:**
- `!slowmode` - Disable slowmode (set to 0)
- `!slowmode <seconds>` - Set slowmode duration
- `!slowmode <seconds> <channel>` - Set slowmode for specific channel

**Parameters:**
- `seconds` - Slowmode duration in seconds (0-21600, 0 to disable)
- `channel` - (Optional) Target channel (defaults to current channel)

**Examples:**
- `!slowmode 0` - Disable slowmode
- `!slowmode 30` - Set 30-second slowmode
- `!slowmode 300 #general` - Set 5-minute slowmode in #general

**Features:**
- Supports Discord's full slowmode range (up to 6 hours)
- Smart duration formatting for display
- Can target specific channels
- Works only on text channels

## Permissions

The Moderation plugin defines the following permission nodes:

- `moderation.manage` - Grants full access to all moderation commands.
- `moderation.members.kick` - Permission to kick members
- `moderation.members.ban` - Permission to ban and unban users
- `moderation.members.mute` - Permission for muting (reserved for future features)
- `moderation.members.warn` - Permission for warning system (reserved for future features)
- `moderation.channels.purge` - Permission to delete multiple messages
- `moderation.members.timeout` - Permission to timeout members
- `moderation.channels.slowmode` - Permission to manage channel slowmode

## Safety Features

### Self-Protection
- Prevents users from targeting themselves
- Prevents targeting the bot
- Role hierarchy respect (can't moderate higher-ranked users)

### Comprehensive Logging
- All moderation actions are logged
- Includes moderator information in action logs
- Tracks success/failure of operations
- Includes reasons for all actions

### DM Notifications
- Attempts to notify users before kicks/bans
- Includes server name, reason, and moderator information
- Gracefully handles users with disabled DMs

### Error Handling
- Permission validation before attempting actions
- User-friendly error messages
- Distinction between different types of failures
- Prevents abuse through comprehensive input validation

## Usage Examples

### Member Discipline
```
Moderator: !kick @troubleuser Excessive spam
Bot: ✅ Member Kicked
     @troubleuser has been kicked from the server.
     Reason: Excessive spam
     Moderator: @moderator
```

### Message Management
```
Moderator: !purge 20 @spammer
Bot: ✅ Messages Purged
     Deleted 15 message(s) from @spammer.
     Moderator: @moderator
```

### Channel Control
```
Moderator: !slowmode 60
Bot: 🐌 Slowmode Enabled
     Slowmode has been set to 1 minute(s) in #current-channel.
     Users must wait between sending messages in this channel
```

## Integration

The Moderation plugin integrates with:
- **Permission System:** Respects role-based permissions
- **Logging System:** Records all moderation actions
- **Database:** Stores moderation history and statistics
- **Audit Logs:** Provides detailed action tracking

## Best Practices

### For Moderators
- Always provide clear reasons for moderation actions
- Use appropriate escalation (warn → timeout → kick → ban)
- Monitor message purging to avoid removing important information
- Use slowmode proactively during heated discussions

### For Administrators
- Set up proper role hierarchy to prevent permission abuse
- Review moderation logs regularly
- Train moderators on proper command usage
- Consider implementing warning systems for minor infractions

## Technical Notes

- Uses Discord's native timeout system (introduced in 2021)
- Respects Discord's bulk delete limitations (14-day message age limit)
- Handles both cached and non-cached users appropriately
- Implements proper error handling for network issues
