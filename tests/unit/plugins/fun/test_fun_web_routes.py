"""Tests for the fun plugin web panel routes."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from starlette.testclient import TestClient

from plugins.fun.web.routes import register_fun_routes
from tests.conftest import AsyncContextManager


class MockFunPlugin:
    """Minimal mock FunPlugin for web route testing."""

    def __init__(self, session=None):
        self.session = session

    def render_plugin_template(self, request, template_name, context=None):
        return HTMLResponse("<html><body><div class='game-card'>Panel</div></body></html>")


@pytest.fixture
def app_and_plugin():
    """Build a FastAPI app with fun routes registered against a mock plugin."""
    plugin = MockFunPlugin()
    app = FastAPI()
    register_fun_routes(app, plugin)
    return app, plugin


@pytest.fixture
def client(app_and_plugin):
    """TestClient for the fun web routes."""
    app, _plugin = app_and_plugin
    return TestClient(app)


class TestFunWebRoutes:
    """Test fun plugin web panel routes."""

    def test_panel_page(self, client):
        """Test the main panel page renders."""
        response = client.get("/plugin/fun")
        assert response.status_code == 200
        assert "game-card" in response.text

    # --- Existing routes ---

    def test_dice_route_valid(self, client):
        """Test dice route with valid notation."""
        response = client.post("/plugin/fun/api/roll", data={"dice": "2d6"})
        assert response.status_code == 200
        assert "Rolls:" in response.text or "rolled" in response.text

    def test_dice_route_invalid_format(self, client):
        """Test dice route with invalid format."""
        response = client.post("/plugin/fun/api/roll", data={"dice": "invalid"})
        assert response.status_code == 200
        assert "Error" in response.text or "Invalid" in response.text

    def test_dice_route_out_of_range(self, client):
        """Test dice route with out-of-range dice."""
        response = client.post("/plugin/fun/api/roll", data={"dice": "25d6"})
        assert response.status_code == 200
        assert "Invalid" in response.text or "Range" in response.text

    def test_coinflip_route(self, client):
        """Test coinflip route."""
        response = client.post("/plugin/fun/api/coinflip")
        assert response.status_code == 200
        assert "Heads" in response.text or "Tails" in response.text

    def test_8ball_route_with_question(self, client):
        """Test 8-ball route with a question."""
        response = client.post("/plugin/fun/api/8ball", data={"question": "Will I pass?"})
        assert response.status_code == 200
        assert "Answer:" in response.text

    def test_8ball_route_empty_question(self, client):
        """Test 8-ball route with empty question."""
        response = client.post("/plugin/fun/api/8ball", data={"question": ""})
        assert response.status_code == 200
        assert "question" in response.text.lower()

    def test_random_route_valid(self, client):
        """Test random number route with valid range."""
        response = client.post("/plugin/fun/api/random", data={"min": 1, "max": 10})
        assert response.status_code == 200
        assert "Generated:" in response.text

    def test_random_route_min_gt_max(self, client):
        """Test random route with min > max."""
        response = client.post("/plugin/fun/api/random", data={"min": 20, "max": 10})
        assert response.status_code == 200
        assert "Invalid" in response.text

    def test_random_route_range_too_large(self, client):
        """Test random route with range too large."""
        response = client.post("/plugin/fun/api/random", data={"min": 1, "max": 20_000_000})
        assert response.status_code == 200
        assert "Range" in response.text

    def test_joke_route_api_success(self):
        """Test joke route with successful API call."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"type": "single", "joke": "Test joke"}

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))

        plugin = MockFunPlugin(session=mock_session)
        app = FastAPI()
        register_fun_routes(app, plugin)
        test_client = TestClient(app)

        response = test_client.post("/plugin/fun/api/joke")
        assert response.status_code == 200
        assert "Test joke" in response.text

    def test_joke_route_fallback(self):
        """Test joke route with API failure fallback."""
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=Exception("API error"))

        plugin = MockFunPlugin(session=mock_session)
        app = FastAPI()
        register_fun_routes(app, plugin)
        test_client = TestClient(app)

        response = test_client.post("/plugin/fun/api/joke")
        assert response.status_code == 200
        assert "joke" in response.text.lower()

    def test_quote_route_api_success(self):
        """Test quote route with successful API call."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"content": "Test quote", "author": "Test Author"}

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))

        plugin = MockFunPlugin(session=mock_session)
        app = FastAPI()
        register_fun_routes(app, plugin)
        test_client = TestClient(app)

        response = test_client.post("/plugin/fun/api/quote")
        assert response.status_code == 200
        assert "Test quote" in response.text
        assert "Test Author" in response.text

    def test_quote_route_fallback(self):
        """Test quote route with API failure fallback."""
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=Exception("API error"))

        plugin = MockFunPlugin(session=mock_session)
        app = FastAPI()
        register_fun_routes(app, plugin)
        test_client = TestClient(app)

        response = test_client.post("/plugin/fun/api/quote")
        assert response.status_code == 200
        assert "Quote" in response.text

    # --- New routes ---

    def test_wyr_route(self, client):
        """Test would-you-rather route returns options and vote buttons."""
        response = client.get("/plugin/fun/api/wyr")
        assert response.status_code == 200
        assert "Option A" in response.text
        assert "Option B" in response.text
        assert "wyrVote" in response.text

    def test_meme_route_primary_success(self):
        """Test meme route with primary API success (non-NSFW)."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "title": "Test Meme",
            "url": "https://example.com/meme.png",
            "subreddit": "memes",
            "ups": 42,
            "nsfw": False,
        }

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))

        plugin = MockFunPlugin(session=mock_session)
        app = FastAPI()
        register_fun_routes(app, plugin)
        test_client = TestClient(app)

        response = test_client.post("/plugin/fun/api/meme")
        assert response.status_code == 200
        assert "https://example.com/meme.png" in response.text
        assert "Test Meme" in response.text

    def test_meme_route_nsfw_fallback(self):
        """Test meme route with NSFW primary falling back to Imgflip."""
        nsfw_response = AsyncMock()
        nsfw_response.status = 200
        nsfw_response.json.return_value = {"nsfw": True, "url": "https://example.com/nsfw.png"}

        imgflip_response = AsyncMock()
        imgflip_response.status = 200
        imgflip_response.json.return_value = {
            "success": True,
            "data": {"memes": [{"name": "Drake", "url": "https://imgflip.com/drake.png"}]},
        }

        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=[AsyncContextManager(nsfw_response), AsyncContextManager(imgflip_response)])

        plugin = MockFunPlugin(session=mock_session)
        app = FastAPI()
        register_fun_routes(app, plugin)
        test_client = TestClient(app)

        response = test_client.post("/plugin/fun/api/meme")
        assert response.status_code == 200
        assert "imgflip.com" in response.text or "Imgflip" in response.text

    def test_meme_route_all_apis_fail(self):
        """Test meme route when both APIs fail."""
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=Exception("API error"))

        plugin = MockFunPlugin(session=mock_session)
        app = FastAPI()
        register_fun_routes(app, plugin)
        test_client = TestClient(app)

        response = test_client.post("/plugin/fun/api/meme")
        assert response.status_code == 200
        assert "meme gods" in response.text.lower() or "break" in response.text.lower()

    def test_meme_route_no_session(self):
        """Test meme route with no session available."""
        plugin = MockFunPlugin(session=None)
        app = FastAPI()
        register_fun_routes(app, plugin)
        test_client = TestClient(app)

        response = test_client.post("/plugin/fun/api/meme")
        assert response.status_code == 200
        assert "unavailable" in response.text.lower()

    def test_fact_route_api_success(self):
        """Test fact route with successful API call."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"text": "Test fact from API"}

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))

        plugin = MockFunPlugin(session=mock_session)
        app = FastAPI()
        register_fun_routes(app, plugin)
        test_client = TestClient(app)

        response = test_client.post("/plugin/fun/api/fact")
        assert response.status_code == 200
        assert "Test fact from API" in response.text

    def test_fact_route_api_failure_fallback(self):
        """Test fact route with API failure falling back to DEFAULT_FACTS."""
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=Exception("API error"))

        plugin = MockFunPlugin(session=mock_session)
        app = FastAPI()
        register_fun_routes(app, plugin)
        test_client = TestClient(app)

        response = test_client.post("/plugin/fun/api/fact")
        assert response.status_code == 200
        assert "Fact" in response.text

    def test_fact_route_no_session_fallback(self):
        """Test fact route with no session falling back to DEFAULT_FACTS."""
        plugin = MockFunPlugin(session=None)
        app = FastAPI()
        register_fun_routes(app, plugin)
        test_client = TestClient(app)

        response = test_client.post("/plugin/fun/api/fact")
        assert response.status_code == 200
        assert "Fact" in response.text

    def test_choose_route_valid(self, client):
        """Test choose route with two valid options."""
        response = client.post("/plugin/fun/api/choose", data={"option1": "pizza", "option2": "tacos"})
        assert response.status_code == 200
        assert "pizza" in response.text
        assert "tacos" in response.text
        assert "I choose" in response.text

    def test_choose_route_empty_option(self, client):
        """Test choose route with an empty option."""
        response = client.post("/plugin/fun/api/choose", data={"option1": "", "option2": "tacos"})
        assert response.status_code == 200
        assert "both options" in response.text.lower()
