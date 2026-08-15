## ADDED Requirements

### Requirement: Web Panel Would-You-Rather Card
The plugin SHALL provide a would-you-rather card on the web panel that randomly selects a question from `DEFAULT_WYR_QUESTIONS`, presents two A/B vote buttons, tracks votes client-side, and displays live results with vote counts and percentage bars.

#### Scenario: Load would-you-rather question
- **WHEN** a visitor opens the fun panel and the would-you-rather card loads
- **THEN** the plugin SHALL randomly select a question pair from `DEFAULT_WYR_QUESTIONS` and render both options with A and B vote buttons

#### Scenario: Vote on option A
- **WHEN** a visitor clicks the Option A button
- **THEN** the card SHALL increment the Option A vote count, display a live results bar showing the percentage split between A and B, and update the total vote count

#### Scenario: Vote on option B
- **WHEN** a visitor clicks the Option B button
- **THEN** the card SHALL increment the Option B vote count, display a live results bar showing the percentage split between A and B, and update the total vote count

#### Scenario: Vote tracking is client-side and ephemeral
- **WHEN** a visitor votes and then reloads the panel
- **THEN** the vote counts SHALL reset to zero because the web panel does not persist votes, matching the ephemeral nature of the Discord Miru view

### Requirement: Web Panel Meme Card
The plugin SHALL provide a meme card on the web panel that fetches a meme image from the primary meme API with fallback to the secondary Imgflip API, displays the image inline, and provides a button to fetch a new meme.

#### Scenario: Fetch meme from primary API
- **WHEN** a visitor clicks the "Get new meme" button and the primary meme API returns a non-NSFW meme
- **THEN** the card SHALL display the meme image, title, subreddit, and upvote count

#### Scenario: Primary API fails or returns NSFW
- **WHEN** the primary meme API fails or returns an NSFW meme
- **THEN** the card SHALL fall back to the secondary Imgflip API and display a random meme image with its name

#### Scenario: All meme APIs fail
- **WHEN** both the primary and secondary meme APIs fail
- **THEN** the card SHALL display a friendly "meme gods are taking a break" message

#### Scenario: No HTTP session available
- **WHEN** the plugin's HTTP session is not initialized
- **THEN** the card SHALL display a service-unavailable message

### Requirement: Web Panel Fact Card
The plugin SHALL provide a fact card on the web panel that fetches a random fact from the configured fact API with fallback to `DEFAULT_FACTS`, displayed behind a "Get a fact" button.

#### Scenario: Fetch fact from API
- **WHEN** a visitor clicks the "Get a fact" button and the fact API is available
- **THEN** the card SHALL fetch a random fact and display it with an educational emoji

#### Scenario: API failure fallback
- **WHEN** the fact API fails or returns no text
- **THEN** the card SHALL randomly select a fact from `DEFAULT_FACTS` and display it

#### Scenario: No HTTP session available
- **WHEN** the plugin's HTTP session is not initialized
- **THEN** the card SHALL fall back to `DEFAULT_FACTS` and display a randomly selected fact

### Requirement: Web Panel Choose Card
The plugin SHALL provide a choose card on the web panel with two text inputs and a button that randomly selects one of the two provided options and displays the result with both options listed.

#### Scenario: Choose between two options
- **WHEN** a visitor enters two non-empty options and clicks the "Choose for me" button
- **THEN** the card SHALL randomly select one option and display the chosen result with both options listed

#### Scenario: Empty option provided
- **WHEN** a visitor clicks the "Choose for me" button with one or both inputs empty
- **THEN** the card SHALL display an error message requesting both options

### Requirement: Web Panel Route Tests
The plugin SHALL include tests covering all web panel routes, verifying that each endpoint returns the expected HTML response for valid input, invalid input, and error conditions.

#### Scenario: Test existing game routes
- **WHEN** the web panel test suite runs against the dice, coinflip, 8-ball, random, joke, and quote routes
- **THEN** each route SHALL be exercised with valid input, invalid input where applicable, and API-failure fallback paths, asserting the returned HTML contains expected content

#### Scenario: Test new card routes
- **WHEN** the web panel test suite runs against the would-you-rather, meme, fact, and choose routes
- **THEN** each route SHALL be exercised with valid input, empty/invalid input where applicable, and API-failure fallback paths, asserting the returned HTML contains expected content

#### Scenario: Test panel page renders
- **WHEN** the web panel test suite requests the main panel page
- **THEN** the response SHALL be an HTML page containing all game cards

### Requirement: Command Test Coverage
The plugin SHALL include command tests for the would-you-rather, meme, and fact commands, which are currently untested.

#### Scenario: Would-you-rather command test
- **WHEN** the test suite exercises the would-you-rather command with a mocked Miru client
- **THEN** the command SHALL respond with an embed containing both options and SHALL start the view when a Miru client is present

#### Scenario: Would-you-rather without Miru
- **WHEN** the would-you-rather command runs without a Miru client on the bot
- **THEN** the command SHALL respond with the embed only and SHALL not attempt to start a view

#### Scenario: Meme command API success test
- **WHEN** the meme command runs with a mocked session returning a non-NSFW primary API response
- **THEN** the command SHALL respond with an embed containing the meme image

#### Scenario: Meme command fallback test
- **WHEN** the primary meme API fails or returns NSFW and the secondary Imgflip API succeeds
- **THEN** the command SHALL respond with an embed containing the Imgflip meme image

#### Scenario: Fact command API success test
- **WHEN** the fact command runs with a mocked session returning a valid fact
- **THEN** the command SHALL respond with an embed containing the fact text

#### Scenario: Fact command fallback test
- **WHEN** the fact API fails and the session is present
- **THEN** the command SHALL fall back to `DEFAULT_FACTS` and respond with an embed

### Requirement: Would-You-Rather View Tests
The plugin SHALL include tests for `WouldYouRatherView` covering vote toggling, result bar rendering, and percentage calculation.

#### Scenario: Vote for option A
- **WHEN** a user votes for option A via the view callback
- **THEN** the view SHALL record the user's vote for option A, remove any prior vote for option B, and update the results embed with the new counts and percentages

#### Scenario: Toggle vote off
- **WHEN** a user who already voted for option A votes for option A again
- **THEN** the view SHALL remove the user's vote for option A and update the results with zero total votes showing equal percentages

#### Scenario: Percentage calculation with mixed votes
- **WHEN** option A has 3 votes and option B has 1 vote
- **THEN** the results embed SHALL show option A at 75.0% and option B at 25.0% with a total of 4 votes

## MODIFIED Requirements

### Requirement: Random Choice
The plugin SHALL provide a command to randomly choose between two provided options, gated behind the `basic.fun.games.play` permission node. Both options are required arguments enforced by the command framework before the handler executes.

#### Scenario: Choose between two options
- **WHEN** a user with the `basic.fun.games.play` permission runs `/choose pizza tacos`
- **THEN** plugin SHALL randomly select one option and display the chosen result with both options listed

#### Scenario: Insufficient options
- **WHEN** a user provides fewer than 2 options (i.e., omits one of the two required arguments)
- **THEN** the command framework SHALL reject the invocation before the handler runs, requiring both options to be supplied

#### Scenario: Permission denied
- **WHEN** a user lacking the `basic.fun.games.play` permission runs `/choose pizza tacos`
- **THEN** plugin SHALL deny access with an ephemeral error message and not produce a choice
