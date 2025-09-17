# Music Plugin

Advanced music playback functionality with Lavalink integration for high-quality audio streaming in Discord voice channels.

## Overview

The Music plugin provides comprehensive audio playback capabilities for Discord servers. It uses Lavalink for high-quality, low-latency audio streaming and includes advanced features like queue management, search functionality, playback history, and persistent queue storage.

## Architecture

### Core Components
- **Lavalink Integration:** High-performance audio processing server
- **Queue Management:** Persistent queue storage with database backing
- **Event System:** Real-time playback event handling
- **Command Modules:** Organized command structure for different functionalities
- **Voice Management:** Intelligent voice channel handling with auto-disconnect

### Command Modules
The plugin is organized into specialized command modules:
- **Playback:** Play, pause, stop, skip, volume control
- **Queue:** Queue management, shuffle, repeat modes
- **Voice:** Join, leave, move voice channel controls
- **Search:** Music search and browsing capabilities
- **Now Playing:** Current track information and controls
- **Settings:** Bot behavior configuration
- **History:** Playback history and recently played tracks

## Features

### Audio Playback
- **Multi-Source Support:** YouTube, Spotify, SoundCloud, direct links
- **High-Quality Streaming:** Lavalink-powered audio processing
- **Volume Control:** Per-server volume settings with smooth transitions
- **Crossfade Support:** Seamless track transitions

### Queue Management
- **Unlimited Queue Size:** Add hundreds of tracks
- **Queue Persistence:** Queues survive bot restarts
- **Smart Shuffling:** Intelligent random track selection
- **Repeat Modes:** Track, queue, and off modes
- **Queue History:** Track previously played songs

### Voice Channel Intelligence
- **Auto-Join:** Joins user's voice channel automatically
- **Auto-Disconnect:** Leaves empty channels to save resources
- **Channel Switching:** Move between voice channels seamlessly
- **Permission Handling:** Respects voice channel permissions

### Search & Discovery
- **Multi-Platform Search:** Search across multiple music platforms
- **Search Results:** Browse and select from search results
- **Playlist Support:** Add entire playlists with one command
- **Smart Suggestions:** AI-powered music recommendations

## Core Commands

*Note: The Music plugin uses a modular command system. Individual commands are defined in separate command modules. Below are the key command categories:*

### Playback Control Commands
- **Play:** Start playback or add tracks to queue
- **Pause/Resume:** Control playback state
- **Stop:** Stop playback and clear queue
- **Skip:** Skip to next track
- **Volume:** Adjust playback volume

### Queue Management Commands
- **Queue:** View current queue
- **Shuffle:** Randomize queue order
- **Repeat:** Set repeat modes
- **Clear:** Clear the queue
- **Remove:** Remove specific tracks

### Voice Channel Commands
- **Join:** Connect to voice channel
- **Leave:** Disconnect from voice channel
- **Move:** Switch voice channels

### Information Commands
- **Now Playing:** Display current track information
- **Search:** Search for music
- **History:** View playback history

## Technical Requirements

### External Dependencies
- **Lavalink Server:** Audio processing server (configured separately)
- **Java Runtime:** Required for Lavalink server operation
- **Network Connectivity:** Stable connection for streaming

### Configuration
The plugin requires the following settings (configured in `config/settings.py`):
```python
lavalink_host = "localhost"      # Lavalink server host
lavalink_port = 2333            # Lavalink server port
lavalink_password = "youshallnotpass"  # Lavalink server password
```

### Lavalink Configuration
The plugin expects a Lavalink server configuration file at `lavalink/application.yml`. See the existing configuration for reference.

## Database Integration

### Persistent Queues
- Queue states are automatically saved to database
- Queues are restored on bot startup
- Tracks maintain metadata and positioning

### Playback History
- All played tracks are logged
- History includes timestamps and user information
- Searchable history for track discovery

### Settings Storage
- Server-specific settings (volume, repeat modes)
- User preferences and customizations
- Plugin configuration persistence

## Event Handling

### Playback Events
- **Track Start:** Triggered when a track begins playing
- **Track End:** Handles track completion and queue advancement
- **Track Error:** Manages playback failures and recovery
- **Queue Empty:** Handles end-of-queue scenarios

### Voice Events
- **Voice State Updates:** Monitors user voice channel activity
- **Channel Empty Detection:** Implements smart auto-disconnect
- **Connection Management:** Handles voice connection lifecycle

## Performance Features

### Resource Optimization
- **Lazy Loading:** Commands loaded on-demand
- **Connection Pooling:** Efficient HTTP session management
- **Memory Management:** Automatic cleanup of unused resources
- **CPU Optimization:** Efficient event handling and processing

### Scalability
- **Multi-Server Support:** Independent queues per server
- **Concurrent Playback:** Multiple servers simultaneously
- **Load Balancing:** Intelligent resource distribution

## Error Handling & Recovery

### Network Issues
- **Connection Retry Logic:** Automatic reconnection attempts
- **Fallback Sources:** Multiple source fallbacks for tracks
- **Timeout Handling:** Graceful handling of network timeouts
- **Rate Limit Management:** Intelligent API usage

### Playback Errors
- **Track Skipping:** Automatic skip of unplayable tracks
- **Queue Recovery:** Maintains queue integrity during errors
- **State Synchronization:** Keeps bot state consistent
- **Error Reporting:** User-friendly error messages

## Integration Points

### Bot Framework Integration
- **Command System:** Full integration with bot command framework
- **Permission System:** Respects server permission configurations
- **Event System:** Participates in bot-wide event handling
- **Database:** Uses shared database connection pool

### Discord Integration
- **Voice API:** Direct integration with Discord voice systems
- **Rich Embeds:** Interactive music information displays
- **Reaction Controls:** Emoji-based playback controls
- **Status Updates:** Bot status reflects current playback

## Development Notes

### Plugin Architecture
The Music plugin follows a modular architecture pattern:
```
music_plugin.py          # Main plugin class and initialization
events.py               # Event handlers for playback events
utils.py                # Utility functions for queue and history management
views.py                # Interactive Discord UI components
commands/               # Modular command implementations
├── playback.py        # Playback control commands
├── queue.py           # Queue management commands
├── voice.py           # Voice channel commands
├── search.py          # Search and discovery commands
├── nowplaying.py      # Current track information
├── settings.py        # Configuration commands
└── history.py         # Playback history commands
```

### Extension Points
The plugin architecture supports easy extension:
- **New Commands:** Add commands to existing modules
- **New Sources:** Extend search functionality
- **Custom Events:** Add new event handlers
- **UI Components:** Create new interactive elements

## Troubleshooting

### Common Issues
1. **Lavalink Connection:** Ensure Lavalink server is running and accessible
2. **Voice Permissions:** Verify bot has voice channel access permissions
3. **Audio Quality:** Check Lavalink server resources and network stability
4. **Queue Persistence:** Ensure database connectivity for queue storage

### Debug Information
The plugin provides extensive logging for troubleshooting:
- Playback state changes
- Queue operations
- Voice connection events
- Error conditions and recovery attempts

## Future Enhancements

### Planned Features
- **Lyrics Integration:** Display synchronized lyrics
- **Playlist Management:** Save and share custom playlists
- **Radio Modes:** Continuous playback with smart recommendations
- **Audio Effects:** Equalizer, filters, and audio enhancements
- **Social Features:** Collaborative playlists and voting systems
