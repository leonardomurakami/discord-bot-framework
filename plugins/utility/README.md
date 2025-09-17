# Utility Plugin

Utility commands for server management and tools including user information, avatars, timestamps, color tools, and encoding/hashing utilities.

## Overview

The Utility plugin provides a comprehensive set of tools for Discord server management and general utility functions. It includes commands for user information display, timestamp conversion, color analysis, text encoding/decoding, and cryptographic hashing.

## Commands

### User Information

#### `!userinfo` (Aliases: `!user`, `!whois`, `/userinfo`)
Get detailed information about a Discord user.

**Permission Required:** `utility.info`

**Usage:**
- `!userinfo` - Get information about yourself
- `!userinfo @user` - Get information about specified user

**Information Displayed:**
- User ID and display name
- Bot account status
- Account creation date
- Server join date (if in server)
- User roles and permissions
- Key server permissions (Administrator, Manage Server, etc.)

**Features:**
- Works with users both in and outside the server
- Displays up to 10 roles with overflow indication
- Shows high-level permissions for quick moderation reference
- Handles permission errors gracefully

#### `!avatar` (Aliases: `!av`, `!pfp`, `/avatar`)
Display a user's avatar in high resolution.

**Permission Required:** `utility.info`

**Usage:**
- `!avatar` - Show your own avatar
- `!avatar @user` - Show specified user's avatar

**Features:**
- High-resolution avatar display
- Direct link to avatar URL for external use
- Supports both server-specific and global avatars
- Works with animated avatars

### Time & Date Utilities

#### `!timestamp` (Aliases: `!time`, `!ts`, `/timestamp`)
Convert time inputs to Discord timestamp formats.

**Permission Required:** `utility.convert`

**Usage:**
- `!timestamp` - Current time (default)
- `!timestamp now` - Current time
- `!timestamp 1640995200` - Unix timestamp conversion
- `!timestamp "2024-01-01 12:00"` - Date/time string conversion
- `!timestamp "2024-01-01"` - Date-only conversion

**Supported Input Formats:**
- `YYYY-MM-DD HH:MM` (24-hour format)
- `YYYY-MM-DD HH:MM:SS` (with seconds)
- `YYYY-MM-DD` (date only, assumes 00:00)
- `MM/DD/YYYY HH:MM` (US format with time)
- `MM/DD/YYYY` (US date format)
- Unix timestamp (seconds since epoch)
- `now` keyword for current time

**Discord Timestamp Formats Generated:**
- Default (`<t:timestamp>`)
- Short Time (`<t:timestamp:t>`) - 12:34 PM
- Long Time (`<t:timestamp:T>`) - 12:34:56 PM
- Short Date (`<t:timestamp:d>`) - 01/01/2024
- Long Date (`<t:timestamp:D>`) - January 1, 2024
- Short Date/Time (`<t:timestamp:f>`) - January 1, 2024 12:34 PM
- Long Date/Time (`<t:timestamp:F>`) - Sunday, January 1, 2024 12:34 PM
- Relative (`<t:timestamp:R>`) - 2 hours ago

### Color Utilities

#### `!color` (Aliases: `!colour`, `/color`)
Display detailed information about colors and convert between formats.

**Permission Required:** `utility.tools`

**Usage:**
- `!color #FF0000` - Hex color analysis
- `!color red` - Named color analysis
- `!color #5865F2` - Discord's brand color

**Supported Color Inputs:**
- **Hex Codes:** `#FF0000`, `#00FF00`, `#0000FF`
- **Color Names:** `red`, `green`, `blue`, `yellow`, `cyan`, `magenta`, `black`, `white`, `gray`, `orange`, `purple`, `pink`, `brown`, `gold`, `silver`, `discord`, `blurple`

**Information Displayed:**
- Hex representation
- RGB values
- HSL (Hue, Saturation, Lightness) values
- Decimal color value
- Color preview image
- Visual color swatch

**Features:**
- Color format validation
- Multiple input format support
- Visual color preview generation
- Comprehensive color information display

### Text Processing

#### `!base64` (Aliases: `!b64`, `/base64`)
Encode or decode text using Base64 encoding.

**Permission Required:** `utility.convert`

**Usage:**
- `!base64 encode "Hello World"` - Encode text to Base64
- `!base64 decode "SGVsbG8gV29ybGQ="` - Decode Base64 to text
- `!base64 enc "Text to encode"` - Short form encoding
- `!base64 dec "Base64String="` - Short form decoding

**Features:**
- UTF-8 text encoding support
- Input validation for decode operations
- Handles special characters and Unicode
- Length limits for display (with truncation indicators)
- Error handling for invalid Base64 input

#### `!hash` (Alias: `/hash`)
Generate cryptographic hashes of text using various algorithms.

**Permission Required:** `utility.tools`

**Usage:**
- `!hash md5 "text to hash"` - Generate MD5 hash
- `!hash sha1 "text to hash"` - Generate SHA-1 hash
- `!hash sha256 "text to hash"` - Generate SHA-256 hash

**Supported Algorithms:**
- **MD5:** 128-bit hash function (not recommended for security)
- **SHA-1:** 160-bit hash function (legacy support)
- **SHA-256:** 256-bit hash function (recommended for security)

**Information Displayed:**
- Original input (truncated for security if long)
- Generated hash in hexadecimal format
- Hash algorithm used
- Hash length in characters

**Features:**
- Multiple hash algorithm support
- Input truncation for security (doesn't show full long inputs)
- Hexadecimal output formatting
- UTF-8 text encoding support

## Permissions

The Utility plugin defines the following permission nodes:

- `utility.info` - Access to user information commands (userinfo, avatar)
- `utility.convert` - Access to conversion commands (timestamp, base64)
- `utility.tools` - Access to utility tools (color, hash)

## External Dependencies

### Image Services
- **Placeholder Service:** Uses `https://via.placeholder.com/` for color preview generation
- **Fallback Handling:** Graceful degradation if image services are unavailable

### HTTP Client
- Uses `aiohttp` for making external API requests
- Automatic session management with proper cleanup
- Connection timeout and error handling

## Color Analysis Features

### Color Space Conversions
The plugin includes built-in color space conversion algorithms:
- **RGB to HSL:** Converts Red-Green-Blue to Hue-Saturation-Lightness
- **Hex to RGB:** Parses hexadecimal color codes to RGB values
- **Color Validation:** Ensures proper color format and range validation

### Named Color Support
Pre-defined color mappings for common colors:
- Standard colors (red, green, blue, etc.)
- Web colors (orange, purple, pink, etc.)
- Metallic colors (gold, silver)
- Platform-specific colors (discord, blurple)

## Usage Examples

### User Information
```
User: !userinfo @member
Bot: 👤 Username
     User ID: 123456789
     Display Name: Member Display Name
     Bot Account: No
     Account Created: 2 years ago
     Joined Server: 6 months ago
     Roles: @Member, @Active, @Contributor (+2 more)
     Key Permissions: Manage Messages
```

### Timestamp Conversion
```
User: !timestamp "2024-12-25 00:00"
Bot: 🕒 Discord Timestamps
     Timestamp: 1735084800
     
     Default: <t:1735084800>        Christmas Day 2024
     Short Time: <t:1735084800:t>   12:00 AM
     Relative: <t:1735084800:R>     in 11 months
```

### Color Analysis
```
User: !color #5865F2
Bot: 🎨 Color: #5865F2
     Hex: #5865F2
     RGB: rgb(88, 101, 242)
     HSL: hsl(235°, 86%, 65%)
     Decimal: 5793522
     [Color preview image displayed]
```

### Text Processing
```
User: !base64 encode "Hello World"
Bot: 🔢 Base64 Encoded
     Input: Hello World
     Output: SGVsbG8gV29ybGQ=

User: !hash sha256 "password123"
Bot: 🔐 SHA256 Hash
     Input: password123
     Hash: ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f
     Algorithm: SHA256
     Length: 64 characters
```

## Security Considerations

### Hash Function Usage
- **MD5:** Provided for compatibility but not recommended for security
- **SHA-1:** Legacy support, not recommended for new applications
- **SHA-256:** Recommended for secure hash generation

### Input Sanitization
- All user inputs are properly validated and sanitized
- Length limits prevent abuse and excessive resource usage
- Error handling prevents information disclosure

### Privacy Protection
- User information commands respect Discord privacy settings
- Hash commands truncate long inputs to prevent sensitive data exposure
- No persistent storage of user-provided data

## Error Handling

The plugin includes comprehensive error handling:
- **Network Issues:** Graceful handling of API failures
- **Invalid Input:** User-friendly error messages for incorrect formats
- **Permission Errors:** Clear messaging for access restrictions
- **Resource Limits:** Proper handling of Discord embed and message limits

## Integration

The Utility plugin integrates with:
- **Permission System:** Respects role-based command access
- **Logging System:** Records command usage for analytics
- **Database:** Stores usage statistics and preferences
- **External APIs:** Integrates with color and image services