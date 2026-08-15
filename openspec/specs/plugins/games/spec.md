## Purpose
Provides interactive games including trivia with scoring and achievements, daily angle guessing game, and rock-paper-scissors with persistent statistics and database-backed leaderboards.

## Requirements

### Requirement: Trivia Game
The plugin SHALL provide an interactive trivia command with difficulty selection, category filtering, time attack mode, and scoring.

#### Scenario: Start trivia with filters
- **WHEN** user runs `/trivia medium science`
- **THEN** plugin SHALL fetch question from Open Trivia API with difficulty and category parameters, or fallback to custom questions or defaults, display embed with countdown timer, and attach TriviaView with answer buttons

#### Scenario: Time attack trivia
- **WHEN** trivia question is randomly selected as time attack (10% chance)
- **THEN** plugin SHALL display "Time Attack Trivia!" title and award 1.5x multiplier for fast answers

#### Scenario: Answer trivia correctly
- **WHEN** user clicks correct answer button
- **THEN** plugin SHALL award base points (easy=10, medium=20, hard=30), apply streak bonus (+5 per streak, max +50), update TriviaStats in database, check for achievements, and display result embed

#### Scenario: Answer trivia incorrectly
- **WHEN** user clicks incorrect answer button
- **THEN** plugin SHALL reset current streak to 0, update TriviaStats, and display correct answer

#### Scenario: Use hint
- **WHEN** user clicks hint button
- **THEN** plugin SHALL reveal one incorrect answer, apply 50% point penalty, and mark hint as used in stats

### Requirement: Trivia Statistics
The plugin SHALL provide a command to view detailed trivia statistics for a user.

#### Scenario: View own trivia stats
- **WHEN** user runs `/trivia-stats`
- **THEN** plugin SHALL display embed with total questions, correct answers, accuracy, total points, breakdown by difficulty, current/best streak, fast answers, and hints used

#### Scenario: View another user's stats
- **WHEN** user runs `/trivia-stats @user`
- **THEN** plugin SHALL display stats for the specified user

### Requirement: Trivia Leaderboard
The plugin SHALL provide a command to view server leaderboards with multiple sorting options.

#### Scenario: View points leaderboard
- **WHEN** user runs `/trivia-leaderboard points`
- **THEN** plugin SHALL display top 10 users by total points with medal emojis

#### Scenario: View accuracy leaderboard
- **WHEN** user runs `/trivia-leaderboard accuracy`
- **THEN** plugin SHALL display top 10 users by accuracy (minimum 5 questions)

#### Scenario: View streak leaderboard
- **WHEN** user runs `/trivia-leaderboard streak`
- **THEN** plugin SHALL display top 10 users by best streak

### Requirement: Trivia Achievements
The plugin SHALL provide an achievement system with automatic detection and notification.

#### Scenario: Unlock achievement
- **WHEN** user meets achievement criteria (e.g., 10 correct answers)
- **THEN** plugin SHALL create TriviaAchievement record, send channel notification with embed, and log unlock

#### Scenario: View achievements
- **WHEN** user runs `/trivia-achievements`
- **THEN** plugin SHALL display all unlocked achievements with emoji, name, description, and unlock date

### Requirement: Angle Game
The plugin SHALL provide a daily angle guessing game with 4 attempts, visual feedback, and scoring.

#### Scenario: Start daily angle game
- **WHEN** user runs `/angle`
- **THEN** plugin SHALL generate daily target angle (1-360) seeded by date and user ID, create AngleGame record if not exists, generate protractor image with matplotlib, display embed with visual, and attach AngleView with number input

#### Scenario: Submit angle guess
- **WHEN** user submits a guess via AngleView
- **THEN** plugin SHALL calculate angular distance, provide higher/lower hint, update guesses list, award points if close (exact=100, 1deg=75, 2deg=50), mark game complete after 4 attempts or exact match, and update AngleStats

#### Scenario: Replay after completion
- **WHEN** user runs `/angle` after completing daily game
- **THEN** plugin SHALL start in-memory replay with new random target, no points eligibility, and unlimited attempts

#### Scenario: View angle stats
- **WHEN** user runs `/angle-stats`
- **THEN** plugin SHALL display embed with games played, wins, win rate, total points, exact wins, close wins, and current/best streak

### Requirement: Rock Paper Scissors
The plugin SHALL provide a quick rock-paper-scissors game against the bot.

#### Scenario: Start RPS game
- **WHEN** user runs `/rps`
- **THEN** plugin SHALL display embed with game title and attach RPSView with Rock/Paper/Scissors buttons

#### Scenario: Make RPS move
- **WHEN** user clicks Rock, Paper, or Scissors button
- **THEN** plugin SHALL randomly select bot move, determine winner, edit original message with result, and display outcome

### Requirement: Database Models
The plugin SHALL register and use database models for persistent game statistics.

#### Scenario: Register models on load
- **WHEN** plugin loads via on_load()
- **THEN** plugin SHALL register TriviaStats, TriviaAchievement, CustomQuestion, GuildLeaderboard, AngleGame, AngleStats, AngleAchievement, RPSStats, RPSAchievement models

#### Scenario: Run schema migrations
- **WHEN** plugin loads
- **THEN** plugin SHALL apply additive migrations (e.g., recent_results_json column) using ALTER TABLE IF NOT EXISTS

### Requirement: Custom Questions
The plugin SHALL support guild-specific custom trivia questions.

#### Scenario: Get custom questions
- **WHEN** trivia fetches questions for a guild
- **THEN** plugin SHALL query CustomQuestion table filtered by guild_id, category, and difficulty, and use these before falling back to API or defaults

### Requirement: Scoring System
The plugin SHALL implement a comprehensive scoring system with bonuses and penalties.

#### Scenario: Calculate trivia points
- **WHEN** user answers correctly
- **THEN** plugin SHALL calculate base points by difficulty, add streak bonus (current_streak * 5, max 50), add time attack bonus (1.5x if answered in 10 seconds), and apply hint penalty (0.5x if hint used)

### Requirement: HTTP Session Management
The plugin SHALL manage an aiohttp ClientSession for API calls with proper lifecycle.

#### Scenario: Initialize session on load
- **WHEN** plugin loads via on_load()
- **THEN** plugin SHALL create aiohttp.ClientSession with configured timeout from games_settings

#### Scenario: Close session on unload
- **WHEN** plugin unloads via on_unload()
- **THEN** plugin SHALL close aiohttp.ClientSession gracefully
