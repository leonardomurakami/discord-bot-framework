## ADDED Requirements

### Requirement: Web Panel Section Navigation
The games web panel SHALL organise its features into distinct, navigable sections — Play, Leaderboards, Stats, and Achievements — so that each is reachable without leaving the panel and without a full page reload.

#### Scenario: Switch between panel sections
- **WHEN** an authenticated user selects a different section within /plugin/games
- **THEN** the panel SHALL display that section's content without a full page reload and SHALL preserve the currently selected guild context

#### Scenario: Default section on load
- **WHEN** an authenticated user opens /plugin/games
- **THEN** the panel SHALL load the Play section by default and SHALL make the Leaderboards, Stats, and Achievements sections reachable from the initial view

#### Scenario: Guild context required
- **WHEN** an authenticated user opens a section without a guild selected in the sidebar
- **THEN** the panel SHALL display a prompt to select a server and SHALL NOT attempt to load game data

### Requirement: Web-Playable Trivia
The games web panel SHALL provide an interactive, single-player trivia game using HTMX that fetches a question, accepts an answer, records stats, and returns the result plus the next question.

#### Scenario: Fetch a trivia question
- **WHEN** an authenticated user with a selected guild requests a trivia question (optionally with difficulty and category filters)
- **THEN** the plugin SHALL fetch a question using the same source priority as the Discord command (custom guild questions, then the Open Trivia API, then built-in defaults), shuffle the answer choices, and return an HTMX fragment with the question text, category, difficulty, and one answer button per choice

#### Scenario: Answer trivia correctly on the web
- **WHEN** the user clicks the correct answer button and the choice is POSTed to the trivia answer endpoint
- **THEN** the plugin SHALL determine correctness, calculate points using the same scoring rules as Discord-played trivia (base points by difficulty, streak bonus, time-attack bonus, hint penalty), record the result via the shared trivia stats helper, and return an HTMX fragment showing the outcome and a button to fetch the next question

#### Scenario: Answer trivia incorrectly on the web
- **WHEN** the user clicks an incorrect answer button
- **THEN** the plugin SHALL reset the current streak, record the result via the shared trivia stats helper, reveal the correct answer, and return an HTMX fragment with the outcome and a next-question button

#### Scenario: Trivia timer
- **WHEN** a trivia question is displayed on the web
- **THEN** the panel SHALL show a client-side countdown timer and SHALL apply the time-attack bonus only when the correct answer is submitted within the configured time window

#### Scenario: Unauthenticated trivia play
- **WHEN** an unauthenticated request is sent to the trivia question or answer endpoint
- **THEN** the plugin SHALL return a prompt to log in and SHALL NOT record any stats

#### Scenario: Web trivia is single-player
- **WHEN** a user plays trivia on the web
- **THEN** the game SHALL be single-player (one user answering one question at a time) and SHALL record stats against that user's identity in the selected guild, sharing the same TriviaStats records as Discord-played trivia

### Requirement: Web-Playable Angle Game
The games web panel SHALL provide an interactive daily angle guessing game using HTMX that displays a protractor image, accepts guesses, and returns updated visual feedback and hints.

#### Scenario: Start the daily angle game on the web
- **WHEN** an authenticated user with a selected guild opens the angle game
- **THEN** the plugin SHALL load or create today's angle game for that user and guild using the same daily-seeded target as the Discord command, render the protractor image, and display an HTMX fragment with the image, attempt count, and a guess input form

#### Scenario: Submit an angle guess on the web
- **WHEN** the user submits a guess (1-360) via the angle guess endpoint
- **THEN** the plugin SHALL process the guess through the shared angle game helper, return an updated HTMX fragment with the refreshed protractor image, the direction hint (higher/lower), the degree distance, the remaining attempts, and the points awarded if the game just ended

#### Scenario: Angle game completion on the web
- **WHEN** the user guesses exactly or exhausts 4 attempts
- **THEN** the plugin SHALL mark the game complete, award points for precision (exact=100, 1°=75, 2°=50) for points-eligible games, update AngleStats via the shared helper, and display the final result with the revealed target angle

#### Scenario: Replay after completion on the web
- **WHEN** the user opens the angle game after completing the daily game
- **THEN** the plugin SHALL start a no-points in-memory replay with a fresh random target and unlimited attempts, identical to the Discord replay behaviour

#### Scenario: Angle image generation route
- **WHEN** the web panel requests the angle protractor image for a given target angle
- **THEN** the plugin SHALL generate the matplotlib protractor PNG (same visual as the Discord command) and return it with a PNG content type, without degree labels

#### Scenario: Unauthenticated angle play
- **WHEN** an unauthenticated request is sent to the angle start, guess, or image endpoint
- **THEN** the plugin SHALL return a prompt to log in and SHALL NOT record any stats or create a game record

### Requirement: Web-Playable Rock Paper Scissors
The games web panel SHALL provide an interactive rock-paper-scissors game using HTMX that accepts a move and returns the bot's move and the outcome.

#### Scenario: Make an RPS move on the web
- **WHEN** an authenticated user with a selected guild clicks Rock, Paper, or Scissors and the choice is POSTed to the RPS endpoint
- **THEN** the plugin SHALL randomly select the bot's move, determine the winner, record the result via the shared RPS stats helper, and return an HTMX fragment showing both moves and the outcome

#### Scenario: RPS is replayable on the web
- **WHEN** the user completes an RPS round on the web
- **THEN** the panel SHALL present controls to play again without a full page reload

#### Scenario: Unauthenticated RPS play
- **WHEN** an unauthenticated request is sent to the RPS endpoint
- **THEN** the plugin SHALL return a prompt to log in and SHALL NOT record any stats

### Requirement: Web Leaderboards View
The games web panel SHALL provide a leaderboards view that surfaces the trivia leaderboard for the selected guild with the same sorting options as the `/trivia-leaderboard` command.

#### Scenario: View points leaderboard on the web
- **WHEN** an authenticated user with a selected guild opens the Leaderboards section and selects the points sort
- **THEN** the panel SHALL display the top 10 users by total trivia points with rank indicators

#### Scenario: View accuracy leaderboard on the web
- **WHEN** the user selects the accuracy sort
- **THEN** the panel SHALL display the top 10 users by accuracy, limited to users with at least 5 questions answered

#### Scenario: View streak leaderboard on the web
- **WHEN** the user selects the streak sort
- **THEN** the panel SHALL display the top 10 users by best streak

#### Scenario: Empty leaderboard
- **WHEN** no users in the selected guild have qualifying stats for the chosen sort
- **THEN** the panel SHALL display an informative empty state rather than an empty table

#### Scenario: Unauthenticated leaderboard access
- **WHEN** an unauthenticated request is sent to the leaderboard endpoint
- **THEN** the plugin SHALL return a prompt to log in and SHALL NOT expose user data

### Requirement: Web Stats View
The games web panel SHALL provide a stats view that surfaces detailed trivia and angle statistics for the current user in the selected guild, equivalent to the `/trivia-stats` and `/angle-stats` commands.

#### Scenario: View own trivia stats on the web
- **WHEN** an authenticated user with a selected guild opens the Stats section
- **THEN** the panel SHALL display the user's trivia stats: total questions, correct answers, accuracy, total points, breakdown by difficulty, current and best streak, fast answers, and hints used

#### Scenario: View own angle stats on the web
- **WHEN** an authenticated user with a selected guild opens the Stats section
- **THEN** the panel SHALL display the user's angle stats: games played, wins, win rate, total points, exact wins, close wins, and current and best streak

#### Scenario: Stats for a user who has not played
- **WHEN** the current user has no stats in the selected guild
- **THEN** the panel SHALL display an informative empty state encouraging the user to play

#### Scenario: Unauthenticated stats access
- **WHEN** an unauthenticated request is sent to the stats endpoint
- **THEN** the plugin SHALL return a prompt to log in and SHALL NOT expose user data

### Requirement: Games Plugin Test Coverage
The games plugin SHALL include unit tests covering game logic, web routes, and stats recording, located under `tests/unit/plugins/games/`.

#### Scenario: Test trivia scoring logic
- **WHEN** the trivia scoring tests run
- **THEN** they SHALL verify base points by difficulty, streak bonus calculation (capped at the configured maximum), time-attack multiplier, and hint penalty

#### Scenario: Test angle game logic
- **WHEN** the angle game logic tests run
- **THEN** they SHALL verify daily angle seeding determinism (same user and date yields the same target), angular distance calculation, direction hints, the 4-attempt limit, and points-for-precision awards

#### Scenario: Test RPS outcome determination
- **WHEN** the RPS logic tests run
- **THEN** they SHALL verify win/lose/draw determination for all nine move combinations

#### Scenario: Test web trivia play route
- **WHEN** the web route tests exercise the trivia question fetch and answer submission endpoints
- **THEN** they SHALL verify that an authenticated request returns a question fragment, a correct answer records stats and returns a success fragment, and an unauthenticated request returns a login prompt without recording stats

#### Scenario: Test web angle play route
- **WHEN** the web route tests exercise the angle start, guess, and image endpoints
- **THEN** they SHALL verify that the start endpoint returns a game fragment, the guess endpoint processes the guess and returns updated feedback, the image endpoint returns PNG bytes, and stats are recorded on completion

#### Scenario: Test web RPS play route
- **WHEN** the web route tests exercise the RPS move endpoint
- **THEN** they SHALL verify that an authenticated request returns an outcome fragment and records stats, and an unauthenticated request returns a login prompt

#### Scenario: Test web leaderboards and stats routes
- **WHEN** the web route tests exercise the leaderboard and stats endpoints
- **THEN** they SHALL verify that leaderboards return ranked entries for each sort type, stats return the current user's trivia and angle stats, and empty states are returned when no data exists

#### Scenario: Test stats recording integration
- **WHEN** the stats recording tests run
- **THEN** they SHALL verify that trivia, angle, and RPS results persist to the correct database models and that achievement checks fire after stats are updated
