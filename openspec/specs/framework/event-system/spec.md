## Purpose
Provides a publish/subscribe event bus for asynchronous event-driven communication with middleware hooks for cross-cutting concerns like logging, analytics, and error handling.

## Requirements

### Requirement: Event listener registration
The EventSystem SHALL support registration of event listeners for specific event names through both direct method calls and decorator-based auto-registration.

#### Scenario: Register listener via add_listener
- **WHEN** `add_listener("message_create", callback)` is called
- **THEN** the callback SHALL be added to the internal `_listeners` dict under the "message_create" key

#### Scenario: Register listener via @event_listener decorator
- **WHEN** a plugin method is decorated with `@event_listener("guild_join")`
- **THEN** the method SHALL have `_event_listener` attribute set to "guild_join" for auto-registration during plugin load

### Requirement: Async event publishing
The EventSystem SHALL support asynchronous event publishing that executes all registered listeners concurrently.

#### Scenario: Emit event with listeners
- **WHEN** `emit("user_join", user, guild)` is called with registered listeners
- **THEN** all listeners SHALL be executed concurrently via `asyncio.gather` with the provided args and kwargs

#### Scenario: Emit event with no listeners
- **WHEN** `emit("unknown_event", data)` is called for an event with no registered listeners
- **THEN** the emit SHALL return immediately without error

### Requirement: Middleware hooks
The EventSystem SHALL support middleware that executes in pre and post phases around event listener execution.

#### Scenario: Add middleware via add_middleware
- **WHEN** `add_middleware(logging_middleware)` is called
- **THEN** the middleware SHALL be appended to the `_middleware` list and executed during event emission

#### Scenario: Middleware pre-phase execution
- **WHEN** an event is emitted and middleware is registered
- **THEN** each middleware SHALL be called with `event_context` and `phase="pre"` before listeners execute

#### Scenario: Middleware post-phase execution
- **WHEN** all listeners have completed execution
- **THEN** each middleware SHALL be called with `event_context` and `phase="post"` after listeners

### Requirement: Event stopping via middleware
The EventSystem SHALL allow middleware to stop event propagation by returning False or setting the stopped flag.

#### Scenario: Middleware stops event
- **WHEN** a middleware returns False or sets `event_context["stopped"] = True` during pre-phase
- **THEN** event listener execution SHALL be skipped and emit shall return immediately

### Requirement: Sync and async listener support
The EventSystem SHALL support both synchronous and asynchronous listener functions through automatic detection.

#### Scenario: Execute async listener
- **WHEN** a listener is an async coroutine function
- **THEN** the listener SHALL be awaited via `_call_maybe_async`

#### Scenario: Execute sync listener
- **WHEN** a listener is a regular synchronous function
- **THEN** the listener SHALL be called directly without await via `_call_maybe_async`

### Requirement: Error handling in listeners
The EventSystem SHALL catch and log exceptions from individual listeners without failing other listeners.

#### Scenario: Listener raises exception
- **WHEN** a listener raises an exception during execution
- **THEN** the exception SHALL be caught, logged with the listener name and event name, and other listeners SHALL continue executing

### Requirement: Middleware error handling
The EventSystem SHALL catch and log exceptions from middleware without interrupting event flow.

#### Scenario: Middleware raises exception in pre-phase
- **WHEN** a middleware raises an exception during pre-phase
- **THEN** the exception SHALL be caught and logged, and the next middleware SHALL execute

#### Scenario: Middleware raises exception in post-phase
- **WHEN** a middleware raises an exception during post-phase
- **THEN** the exception SHALL be caught and logged, and the next middleware SHALL execute

### Requirement: Event context creation
The EventSystem SHALL create a context dictionary containing event metadata for middleware consumption.

#### Scenario: Event context contains metadata
- **WHEN** an event is emitted with `emit("event_name", arg1, arg2, key=value)`
- **THEN** the event_context SHALL contain `event_name`, `args` tuple, `kwargs` dict, and `stopped` flag

### Requirement: Listener removal
The EventSystem SHALL support removal of individual listeners and all listeners for an event.

#### Scenario: Remove specific listener
- **WHEN** `remove_listener("message_create", callback)` is called
- **THEN** the specific callback SHALL be removed from the listeners list for that event

#### Scenario: Remove all listeners
- **WHEN** `remove_all_listeners("message_create")` is called
- **THEN** all listeners for "message_create" SHALL be cleared from the internal dict

### Requirement: Query registered events
The EventSystem SHALL provide methods to query registered listeners and event names.

#### Scenario: Get listeners for event
- **WHEN** `get_listeners("message_create")` is called
- **THEN** a copy of the listeners list for that event SHALL be returned

#### Scenario: Get all event names
- **WHEN** `get_all_events()` is called
- **THEN** a list of all registered event names SHALL be returned

### Requirement: Middleware ordering
The EventSystem SHALL execute middleware in the order they were added via `add_middleware`.

#### Scenario: Middleware executes in registration order
- **WHEN** logging_middleware, analytics_middleware, and error_handler_middleware are added in sequence
- **THEN** they SHALL execute in that same order during both pre and post phases
