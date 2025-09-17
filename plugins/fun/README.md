# Fun Plugin

Fun commands and games for entertainment including dice rolling, jokes, quotes, and random generators.

## Overview

The Fun plugin brings entertainment and interactive games to your Discord server. It includes various commands for gaming, random generation, jokes, and inspirational content to keep your community engaged and entertained.

## Commands

### Testing & Basic Commands

#### `!ping` (Alias: `/ping`)
Test command to check if the bot is responding.

**Usage:** `!ping`

**Response:** Displays a "Pong!" message confirming the bot is working correctly.

### Gaming Commands

#### `!roll` (Aliases: `!r`, `/roll`)
Roll dice using standard dice notation.

**Permission Required:** `fun.games`

**Usage:**
- `!roll` - Roll 1d6 (default)
- `!roll 2d6` - Roll two 6-sided dice
- `!roll 1d20` - Roll one 20-sided dice
- `!roll 3d8` - Roll three 8-sided dice

**Features:**
- Supports 1-20 dice per roll
- Supports 2-1000 sides per die
- Shows individual roll results and total
- Validates input format

#### `!coinflip` (Alias: `/coinflip`)
Flip a coin for heads or tails.

**Permission Required:** `fun.games`

**Usage:** `!coinflip`

**Result:** Randomly returns either "Heads" or "Tails" with appropriate emoji.

#### `!8ball` (Alias: `/8ball`)
Ask the magic 8-ball a question.

**Permission Required:** `fun.games`

**Usage:** `!8ball <question>`

**Example:** `!8ball Will it rain today?`

**Features:**
- 20 different traditional magic 8-ball responses
- Displays both your question and the answer
- Responses range from positive to negative to neutral

#### `!random` (Aliases: `!rng`, `!rand`, `/random`)
Generate random numbers within a specified range.

**Permission Required:** `fun.games`

**Usage:**
- `!random` - Generate random number 1-100 (default)
- `!random 50` - Generate random number 1-50
- `!random 10 25` - Generate random number between 10-25

**Features:**
- Customizable min/max range
- Range validation (max 10 million difference)
- Shows total number of possibilities

#### `!choose` (Alias: `/choose`)
Let the bot choose between two options.

**Usage:** `!choose <option1> <option2>`

**Example:** `!choose pizza burgers`

**Features:**
- Makes a random choice between provided options
- Displays all options and the chosen result

### Entertainment Commands

#### `!joke` (Alias: `/joke`)
Get a random joke from online API or local collection.

**Usage:** `!joke`

**Features:**
- Fetches jokes from JokeAPI with content filtering
- Falls back to local joke collection if API is unavailable
- Filters out NSFW, religious, political, racist, sexist, and explicit content
- Supports both single-line and setup/punchline style jokes

#### `!quote` (Aliases: `!inspire`, `!wisdom`, `/quote`)
Get a random inspirational quote.

**Usage:** `!quote`

**Features:**
- Fetches quotes from Quotable API
- Falls back to local inspirational quote collection
- Displays quote text and author
- Includes motivational emoji in footer
- Limits quote length to 150 characters for readability

## Permissions

The Fun plugin defines the following permission nodes:

- `fun.games` - Access to gaming commands (roll, coinflip, 8ball, random)
- `fun.images` - Access to image-related commands (reserved for future use)

Commands without specific permission requirements are available to all users.

## External Dependencies

### APIs Used
- **JokeAPI** (`https://v2.jokeapi.dev/`) - For fetching random jokes
- **Quotable API** (`https://api.quotable.io/`) - For fetching inspirational quotes

### Fallback Behavior
All commands that rely on external APIs include local fallbacks:
- **Jokes:** Built-in collection of clean, family-friendly jokes
- **Quotes:** Curated collection of inspirational quotes from famous figures

## Configuration

The plugin automatically manages HTTP sessions for API requests and handles connection cleanup on plugin unload.

## Error Handling

- **Network Issues:** Graceful fallback to local content when APIs are unavailable
- **Invalid Input:** User-friendly error messages for incorrect command usage
- **Rate Limiting:** Built-in handling of API rate limits with local fallbacks
- **Input Validation:** All user inputs are validated for safe ranges and formats

## Examples

```
User: !roll 3d6
Bot: 🎲 You rolled: 4, 2, 6
     Total: 12

User: !8ball Am I awesome?
Bot: 🎱 Magic 8-Ball
     Question: Am I awesome?
     Answer: It is certain

User: !joke
Bot: 😂 Random Joke
     Why don't scientists trust atoms? Because they make up everything!

User: !quote
Bot: 💭 Inspirational Quote
     "The only way to do great work is to love what you do."
     — Steve Jobs
     💪 Stay inspired!
```

## Notes

- All random generation uses Python's `random` module with appropriate seeding
- API requests include user-agent headers and respect service terms
- The plugin automatically cleans up HTTP sessions when unloaded
- All commands support both prefix and slash command formats
