# Games Plugin Guidelines

## Overview
- Provides interactive games with a focus on trivia featuring enhanced scoring, achievements, and custom questions.
- Supports difficulty levels, category selection, persistent statistics, and guild-specific leaderboards.
- Includes hint system using ephemeral messages and time attack bonuses for competitive gameplay.
- Primary permission nodes:
  - `basic.games.play` – access to basic game features.
  - `games.trivia.play` – access to trivia commands and features.
  - `games.trivia.manage` – manage trivia settings and custom questions.
  - `games.admin.questions` – administrative control over question management.

## Architecture
- `plugin.py` defines `GamesPlugin` which inherits `DatabaseMixin` and `BasePlugin`. It maintains an `aiohttp` session for API calls and registers database models for persistence.
- `commands/`
  - `trivia.py` – Enhanced trivia commands with difficulty/category selection, statistics, and leaderboards.
- `config.py` – Game settings, API endpoints, scoring configurations, achievement definitions, and fallback data.
- `views/` – Interactive UI components:
  - `trivia.py` – `EnhancedTriviaView` with hint system, time attack mode, and enhanced scoring.
- `models/` – Database models kept in their own folder:
  - `trivia.py` – `TriviaStats`, `TriviaAchievement`, `CustomQuestion`, `GuildLeaderboard` models.
- The plugin persists user statistics, achievements, custom questions, and cached leaderboard data.

## Commands
| Command | Description | Permission Node |
| --- | --- | --- |
| `/trivia [difficulty] [category]` | Start interactive trivia with optional filters. Supports easy/medium/hard difficulty and various categories. | `games.trivia.play` |
| `/trivia-stats [user]` | View detailed trivia statistics for yourself or another user. | `games.trivia.play` |
| `/trivia-leaderboard [type]` | View server leaderboards by points, accuracy, or best streak. | `games.trivia.play` |

## Enhanced Features
### Scoring System
- Difficulty-based point values: Easy (10), Medium (20), Hard (30)
- Hint penalty: 50% point reduction when using hints
- Time attack bonuses: 1.5x multiplier for questions answered quickly
- Streak bonuses: Additional points for consecutive correct answers

### Achievement System
- 8 different achievements ranging from first correct answer to mastery milestones
- Automatic achievement detection and awarding
- Persistent achievement tracking per guild

### Custom Questions
- Guild administrators can add custom trivia questions
- Bulk import functionality for adding multiple questions
- Category and difficulty tagging for custom content
- Usage statistics tracking for custom questions

## Configuration
- API endpoints and game settings in `config.py`
- Trivia categories mapped to Open Trivia Database IDs
- Configurable timeouts, scoring multipliers, and limits
- Achievement definitions with requirements and metadata
- Environment variables prefixed with `GAMES_` for customization

## Database Models
### TriviaStats
Tracks comprehensive user statistics including total questions, accuracy, difficulty breakdown, streaks, and timing data.

### TriviaAchievement
Stores unlocked achievements with metadata and unlock timestamps.

### CustomQuestion
Guild-specific custom questions with full trivia data structure and usage tracking.

### GuildLeaderboard
Cached leaderboard data with TTL for performance optimization.

## Development Guidelines
- Always use `plugin.session` for HTTP requests with proper fallbacks to default data
- Register new commands through factory functions and attach via `_register_commands()`
- Use `plugin.smart_respond` for consistent slash/prefix command compatibility
- Leverage database session helpers (`plugin.db_session()`) for all persistence operations
- Update configuration in `config.py` when adding new game mechanics or settings
- Run plugin tests after changes: `uv run pytest tests/unit/plugins/games`

## Troubleshooting
- **API failures**: Commands gracefully fall back to custom questions or defaults when external APIs are unavailable
- **Database errors**: All database operations are wrapped in try-catch blocks with proper logging
- **Achievement issues**: Check achievement requirements in config and ensure proper database session handling
- **Leaderboard problems**: Verify minimum qualification requirements and cache TTL settings

## Future Development
See `TODO.md` for planned advanced features including:
- Multi-round games and tournament mode
- Team collaboration features
- Daily challenges and seasonal events
- Enhanced analytics and performance optimizations
- Additional question sources and community features

Follow these guidelines to maintain consistency with the existing architecture while extending game functionality.