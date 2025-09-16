# Testing Documentation

This directory contains comprehensive test suites for the Discord bot framework, organized to achieve at least 80% code coverage.

## Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── bot/                # Core bot functionality tests
│   │   ├── test_message_handler.py
│   │   ├── test_plugin_loader.py
│   │   ├── test_permissions.py
│   │   ├── test_commands.py
│   │   └── test_base_plugin.py
│   └── plugins/            # Plugin-specific tests
│       ├── admin/
│       ├── fun/
│       ├── moderation/
│       ├── help/
│       └── utility/
├── integration/            # Integration tests (future)
├── fixtures/              # Test fixtures and data
├── conftest.py            # Pytest configuration and fixtures
└── README.md              # This file
```

## Running Tests

### Install Test Dependencies
```bash
pip install -r requirements-test.txt
```

### Run All Tests
```bash
pytest
```

### Run with Coverage Report
```bash
pytest --cov=bot --cov=plugins --cov-report=html --cov-report=term-missing
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/unit/

# Bot core tests only
pytest tests/unit/bot/

# Plugin tests only
pytest tests/unit/plugins/

# Specific plugin tests
pytest tests/unit/plugins/admin/
```

### Run Tests with Verbose Output
```bash
pytest -v
```

### Run Tests and Stop on First Failure
```bash
pytest -x
```

## Test Coverage Goals

The test suite aims for **at least 80% code coverage** across:

- **Core Bot Functionality** (85%+ target)
  - Message handling and command processing
  - Plugin loading and management
  - Permission system
  - Base plugin functionality
  - Command argument parsing

- **Plugin Functionality** (80%+ target)
  - Admin plugin commands
  - Fun plugin commands
  - Moderation plugin commands
  - Utility plugin commands
  - Help system functionality

## Test Categories

### Unit Tests
- Test individual functions and methods in isolation
- Mock external dependencies (database, Discord API, etc.)
- Fast execution for rapid feedback
- Located in `tests/unit/`

### Integration Tests (Future)
- Test component interactions
- Test with real or realistic external services
- Slower execution but more comprehensive
- Located in `tests/integration/`

## Test Fixtures

Common fixtures are provided in `conftest.py`:

- `mock_bot` - Complete bot instance mock
- `mock_hikari_bot` - Hikari bot mock
- `mock_db_manager` - Database manager mock
- `mock_permission_manager` - Permission system mock
- `mock_context` - Command context mock
- `mock_user`, `mock_member`, `mock_guild` - Discord entity mocks

## Writing New Tests

### Test Naming Convention
- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<functionality>`

### Example Test Structure
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from your_module import YourClass


class TestYourClass:
    \"\"\"Test YourClass functionality.\"\"\"

    def test_creation(self, mock_bot):
        \"\"\"Test creating the class.\"\"\"
        instance = YourClass(mock_bot)
        assert instance.bot == mock_bot

    @pytest.mark.asyncio
    async def test_async_method(self, mock_bot, mock_context):
        \"\"\"Test async method.\"\"\"
        instance = YourClass(mock_bot)

        await instance.async_method(mock_context)

        mock_context.respond.assert_called_once()

    def test_error_handling(self, mock_bot):
        \"\"\"Test error handling.\"\"\"
        instance = YourClass(mock_bot)

        # Test that errors are handled gracefully
        # Should not raise exceptions
```

### Async Test Guidelines
- Use `@pytest.mark.asyncio` for async tests
- Mock async methods with `AsyncMock()`
- Use `await` when calling async methods
- Test both success and error cases

### Mocking Guidelines
- Mock external dependencies (Discord API, database, HTTP requests)
- Use `MagicMock` for sync objects, `AsyncMock` for async objects
- Mock at the boundary of your code (not internal implementation)
- Verify mocks were called as expected

## Coverage Reports

### Terminal Report
Shows coverage percentage and missing lines:
```bash
pytest --cov-report=term-missing
```

### HTML Report
Generates detailed HTML coverage report:
```bash
pytest --cov-report=html
open htmlcov/index.html
```

### Fail if Coverage Below Threshold
```bash
pytest --cov-fail-under=80
```

## Continuous Integration

Tests should be run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Tests
  run: |
    pip install -r requirements-test.txt
    pytest --cov=bot --cov=plugins --cov-fail-under=80
```

## Test Data and Fixtures

### Using Fixtures
```python
def test_with_fixtures(mock_bot, mock_context, mock_user):
    # Fixtures are automatically injected
    assert mock_user.id == 111111111
```

### Custom Fixtures
Add custom fixtures to `conftest.py` or test files:
```python
@pytest.fixture
def custom_data():
    return {"key": "value"}
```

## Performance Testing

For performance-sensitive code:
```python
import time

def test_performance():
    start = time.time()
    # Your code here
    duration = time.time() - start
    assert duration < 1.0  # Should complete in under 1 second
```

## Best Practices

1. **Test Edge Cases** - Test error conditions, boundary values, empty inputs
2. **Keep Tests Isolated** - Each test should be independent
3. **Use Descriptive Names** - Test names should clearly describe what's being tested
4. **Mock External Dependencies** - Don't rely on external services in unit tests
5. **Test Both Success and Failure** - Verify error handling works correctly
6. **Keep Tests Fast** - Unit tests should run quickly for rapid feedback
7. **Verify Behavior** - Test that the right methods are called with right parameters
8. **Clean Up** - Use fixtures and proper teardown to avoid test pollution

## Coverage Exclusions

Some code may be excluded from coverage:
- Debug/development code
- Error handling for truly exceptional cases
- Code that requires integration testing

Mark exclusions in code:
```python
# pragma: no cover
```

## Debugging Tests

### Run Single Test
```bash
pytest tests/unit/bot/test_message_handler.py::TestMessageCommandHandler::test_handler_creation -v
```

### Drop into Debugger
```python
import pytest

def test_something():
    # Your test code
    pytest.set_trace()  # Debugger will stop here
```

### Print Debug Info
```bash
pytest -s  # Don't capture stdout
```