## Purpose
Provides entertainment commands including dice games, coin flips, magic 8-ball, random choices, and content fetching (jokes, quotes, memes, facts) with API integration and fallback data.

## Requirements

### Requirement: Dice Rolling
The plugin SHALL provide a dice rolling command supporting NdN notation with configurable limits.

#### Scenario: Roll single die
- **WHEN** user runs `/roll 1d6`
- **THEN** plugin SHALL parse dice notation, validate against DICE_LIMITS (1-20 dice, 2-1000 sides), generate random roll, and display result

#### Scenario: Roll multiple dice
- **WHEN** user runs `/roll 2d20`
- **THEN** plugin SHALL display individual rolls and total sum

#### Scenario: Invalid dice format
- **WHEN** user runs `/roll invalid`
- **THEN** plugin SHALL display error message explaining valid NdN format

#### Scenario: Dice out of range
- **WHEN** user runs `/roll 25d6` (exceeds max 20 dice)
- **THEN** plugin SHALL display error message with valid range

### Requirement: Coin Flip
The plugin SHALL provide a coin flip command with random heads/tails result.

#### Scenario: Flip coin
- **WHEN** user runs `/coinflip`
- **THEN** plugin SHALL randomly select "Heads" or "Tails" and display result with coin emoji

### Requirement: Magic 8-Ball
The plugin SHALL provide a magic 8-ball command with predefined responses.

#### Scenario: Ask 8-ball a question
- **WHEN** user runs `/8ball Will I win?`
- **THEN** plugin SHALL randomly select from 20 predefined responses and display with the question

### Requirement: Random Choice
The plugin SHALL provide a command to randomly choose between options.

#### Scenario: Choose between two options
- **WHEN** user runs `/choose pizza tacos`
- **THEN** plugin SHALL randomly select one option and display with both options listed

#### Scenario: Insufficient options
- **WHEN** user provides fewer than 2 options
- **THEN** plugin SHALL display error message requiring at least 2 options

### Requirement: Random Number Generation
The plugin SHALL provide a command to generate random numbers within a range.

#### Scenario: Generate random number
- **WHEN** user runs `/random 1 100`
- **THEN** plugin SHALL validate range (max difference <= RANDOM_NUMBER_LIMIT), generate random integer, and display with range info

#### Scenario: Invalid range
- **WHEN** user runs `/random 100 1` (min > max)
- **THEN** plugin SHALL display error message

### Requirement: Would You Rather
The plugin SHALL provide an interactive would-you-rather command with button voting.

#### Scenario: Start would-you-rather
- **WHEN** user runs `/would-you-rather`
- **THEN** plugin SHALL randomly select from DEFAULT_WYR_QUESTIONS, display embed with two options, and attach Miru view with A/B buttons

#### Scenario: Vote on option
- **WHEN** user clicks option A or B button
- **THEN** view SHALL update embed with vote counts and disable buttons

### Requirement: Joke Fetching
The plugin SHALL provide a joke command with API integration and fallback to default jokes.

#### Scenario: Fetch joke from API
- **WHEN** user runs `/joke` and API is available
- **THEN** plugin SHALL fetch from joke API, parse single/two-part format, and display joke

#### Scenario: API failure fallback
- **WHEN** user runs `/joke` and API fails
- **THEN** plugin SHALL randomly select from DEFAULT_JOKES and display

### Requirement: Quote Fetching
The plugin SHALL provide a quote command with API integration and fallback to default quotes.

#### Scenario: Fetch quote from API
- **WHEN** user runs `/quote` and API is available
- **THEN** plugin SHALL fetch from quote API, extract content and author, and display with motivational emoji

#### Scenario: API failure fallback
- **WHEN** user runs `/quote` and API fails
- **THEN** plugin SHALL randomly select from DEFAULT_QUOTES and display

### Requirement: Meme Fetching
The plugin SHALL provide a meme command with primary and secondary API endpoints and NSFW filtering.

#### Scenario: Fetch meme from primary API
- **WHEN** user runs `/meme` and primary API returns non-NSFW meme
- **THEN** plugin SHALL display embed with image, subreddit, upvotes, and source link

#### Scenario: Primary API fails or NSFW
- **WHEN** primary API fails or returns NSFW content
- **THEN** plugin SHALL fallback to secondary Imgflip API and display random meme

#### Scenario: All APIs fail
- **WHEN** both meme APIs fail
- **THEN** plugin SHALL display friendly "meme gods taking a break" message

### Requirement: Fact Fetching
The plugin SHALL provide a fact command with API integration and fallback to default facts.

#### Scenario: Fetch fact from API
- **WHEN** user runs `/fact` and API is available
- **THEN** plugin SHALL fetch from fact API and display with educational emoji

#### Scenario: API failure fallback
- **WHEN** user runs `/fact` and API fails
- **THEN** plugin SHALL randomly select from DEFAULT_FACTS and display

### Requirement: HTTP Session Management
The plugin SHALL manage an aiohttp ClientSession for API calls with proper lifecycle.

#### Scenario: Initialize session on load
- **WHEN** plugin loads via on_load()
- **THEN** plugin SHALL create aiohttp.ClientSession with configured timeout

#### Scenario: Close session on unload
- **WHEN** plugin unloads via on_unload()
- **THEN** plugin SHALL close aiohttp.ClientSession gracefully
