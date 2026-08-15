## Purpose
Provides a collection of practical utility commands for user information, text conversion, color analysis, and productivity tools including weather lookup, QR codes, polls, and historical events.

## Requirements

### Requirement: Information Commands
The plugin SHALL provide commands for displaying user and server information with external API integration.

#### Scenario: Display user information
- **WHEN** a user with `basic.utility.info.view` permission invokes `/userinfo [user]`
- **THEN** the bot SHALL display an embed with user ID, display name, bot status, account creation date, server join date, roles (up to 10), and key permissions

#### Scenario: Display user avatar
- **WHEN** a user with `basic.utility.info.view` permission invokes `/avatar [user]`
- **THEN** the bot SHALL display an embed with the user's high-resolution avatar image and direct URL

#### Scenario: Display weather information
- **WHEN** a user with `basic.utility.info.view` permission invokes `/weather <location>`
- **THEN** the bot SHALL fetch data from wttr.in API and display temperature, conditions, wind, humidity, visibility, and UV index, or provide fallback message if API unavailable

### Requirement: Conversion Commands
The plugin SHALL provide commands for text and data conversion including timestamps, colors, base64, hashing, and translation helpers.

#### Scenario: Convert time to Discord timestamps
- **WHEN** a user with `basic.utility.convert.use` permission invokes `/timestamp [time_input]` with format YYYY-MM-DD HH:MM, Unix timestamp, or "now"
- **THEN** the bot SHALL parse the input and display all Discord timestamp formats (default, short time, long time, short date, long date, short date/time, long date/time, relative)

#### Scenario: Display color information
- **WHEN** a user with `basic.utility.tools.use` permission invokes `/color <color_input>` with hex code (#FF0000) or color name
- **THEN** the bot SHALL convert to RGB and HSL, display hex, RGB, HSL, and decimal values, and show a color preview image

#### Scenario: Encode or decode base64
- **WHEN** a user with `basic.utility.convert.use` permission invokes `/base64 <encode|decode> <text>`
- **THEN** the bot SHALL perform the base64 operation, truncate output to 1024 characters if needed, and display input and output

#### Scenario: Generate text hash
- **WHEN** a user with `basic.utility.tools.use` permission invokes `/hash <algorithm> <text>` with algorithm md5, sha1, or sha256
- **THEN** the bot SHALL generate the hash using the specified algorithm and display the hash value and length

#### Scenario: Provide translation helper
- **WHEN** a user with `basic.utility.convert.use` permission invokes `/translate <target_language> <text>` with valid language code
- **THEN** the bot SHALL validate the language code (from TRANSLATE_LANGUAGE_CODES), display the original text and target language, and provide links to external translation services

### Requirement: Productivity Tool Commands
The plugin SHALL provide commands for QR codes, polls, and historical event lookup.

#### Scenario: Generate QR code
- **WHEN** a user with `basic.utility.tools.use` permission invokes `/qr <text>` with text up to 1000 characters
- **THEN** the bot SHALL generate a QR code image using api.qrserver.com and display it with text length and type (URL or text)

#### Scenario: Create reaction poll
- **WHEN** a user with `basic.utility.tools.use` permission invokes `/poll <question> <option1> <option2> [option3] [option4]`
- **THEN** the bot SHALL create an embed with the question and options, add number emoji reactions (1-4), and display voting instructions

#### Scenario: Display historical events
- **WHEN** a user with `basic.utility.tools.use` permission invokes `/onthisday <date>` with timedelta format (5m, 1h, 20d) or dd/mm/yyyy
- **THEN** the bot SHALL fetch data from Wikipedia API, display up to 3 selected events, 2 births, and 2 deaths for that date, with formatted timestamps

### Requirement: Utility Configuration
The plugin SHALL load configuration constants for colors, limits, and mappings.

#### Scenario: Load utility configuration
- **WHEN** the UtilityPlugin initializes
- **THEN** the plugin SHALL load embed colors (INFO_COLOR, AVATAR_COLOR, TIMESTAMP_COLOR, COLOR_TOOL_COLOR, etc.), COLOR_NAME_MAP with 20+ color names, TIMESTAMP_FORMATS, BASE64_ACTIONS, HASH_ALGORITHMS, REMINDER_MAX_MINUTES (10080), QR_TEXT_LIMIT (1000), POLL_MAX_OPTIONS (4), and TRANSLATE_LANGUAGE_CODES with 20+ languages

#### Scenario: Validate QR code text length
- **WHEN** a user invokes `/qr` with text exceeding 1000 characters
- **THEN** the bot SHALL reject the request with an error message indicating the character limit

#### Scenario: Validate poll option count
- **WHEN** a user attempts to create a poll with more than 4 options
- **THEN** the bot SHALL reject the request with an error message indicating the maximum option limit

#### Scenario: Validate translation text length
- **WHEN** a user invokes `/translate` with text exceeding 500 characters
- **THEN** the bot SHALL reject the request with an error message indicating the character limit

### Requirement: HTTP Session Management
The plugin SHALL maintain an aiohttp ClientSession for external API requests with graceful degradation.

#### Scenario: Initialize HTTP session on load
- **WHEN** the UtilityPlugin loads
- **THEN** the plugin SHALL create an aiohttp.ClientSession for making HTTP requests

#### Scenario: Close HTTP session on unload
- **WHEN** the UtilityPlugin unloads
- **THEN** the plugin SHALL close the aiohttp.ClientSession to release resources

#### Scenario: Handle unavailable HTTP session
- **WHEN** a command requiring HTTP requests executes but plugin.session is None
- **THEN** the bot SHALL display a service unavailable error message with fallback suggestions

### Requirement: Utility Helper Functions
The plugin SHALL provide helper functions for common conversions and validations.

#### Scenario: Parse timestamp input
- **WHEN** the parse_timestamp_input function receives a time string
- **THEN** the function SHALL handle "now" keyword, Unix timestamps, and multiple date formats (YYYY-MM-DD HH:MM, YYYY-MM-DD, MM/DD/YYYY HH:MM, MM/DD/YYYY)

#### Scenario: Convert RGB to HSL
- **WHEN** the rgb_to_hsl function receives RGB values
- **THEN** the function SHALL return HSL values with hue (0-360), saturation (0-100), and lightness (0-100)

#### Scenario: Chunk text into segments
- **WHEN** the chunk_text function receives text and a limit
- **THEN** the function SHALL yield text segments within the specified limit
