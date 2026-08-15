## Why

The fun plugin's web panel ships only 6 of the 11 Discord commands as interactive HTMX cards, leaving would-you-rather, meme, fact, and choose without panel equivalents. Because the framework is the product and the fun panel is meant to demonstrate complete command/panel parity, this gap undercuts the showcase value. Compounding the problem, the `/choose` command carries a dead validation branch and is missing its `basic.fun.games.play` permission node, and `plugins/fun/AGENTS.md` falsely describes the panel as "a placeholder."

## What Changes

- Add a would-you-rather web card: two A/B buttons with client-side vote tracking and live results bars (no persistence, matching the ephemeral nature of the Discord view).
- Add a meme web card: fetches from the primary meme API with Imgflip fallback, renders the image inline, and provides a "Get new meme" button. Respects the `basic.fun.images.view` permission node for parity with the Discord command.
- Add a fact web card: fetches a random fact from the configured API with fallback to `DEFAULT_FACTS`, displayed behind a "Get a fact" button.
- Add a choose web card: two text inputs plus a "Choose for me" button that returns a random pick with both options listed.
- Fix the `/choose` command: add the missing `permission_node="basic.fun.games.play"` and remove the unreachable `len(choices) < 2` branch (choices is always exactly two from the two required arguments).
- Add web panel route tests for all 7 existing routes plus the 4 new routes (would-you-rather, meme, fact, choose).
- Add command tests for the currently untested would-you-rather, meme, and fact commands.
- Add view tests for `WouldYouRatherView` (vote toggling, result bar rendering, tie-breaking percentages).
- Update `plugins/fun/AGENTS.md` to remove the false "placeholder" claim and document the actual web panel features and routes.

## Capabilities

### New Capabilities

None — this modifies an existing capability.

### Modified Capabilities

- `plugins/fun`: Adds web panel requirements for would-you-rather, meme, fact, and choose cards so the panel achieves full command/panel parity; fixes the choose command's missing permission node and dead validation code; adds requirements for web panel route tests, command tests for the three untested commands, and view tests for `WouldYouRatherView`.

## Impact

- **Code**: `plugins/fun/web/routes.py` gains four new FastAPI endpoints (`/plugin/fun/api/wyr`, `/plugin/fun/api/meme`, `/plugin/fun/api/fact`, `/plugin/fun/api/choose`). `plugins/fun/templates/panel.html` gains four new game cards. `plugins/fun/commands/games.py` is edited to add the `permission_node` to the `choose` command and remove the dead `len(choices) < 2` branch.
- **Permissions**: The `/choose` command now enforces `basic.fun.games.play`, aligning it with `/roll`, `/coinflip`, `/8ball`, `/random`, and `/would-you-rather`. No new permission nodes are introduced.
- **APIs/dependencies**: No new third-party packages. The new meme and fact routes reuse the existing `plugin.session` (`aiohttp.ClientSession`) and the same `API_ENDPOINTS`/`DEFAULT_*` fallback data already used by the Discord commands.
- **Tests**: New `tests/unit/plugins/fun/test_fun_web_routes.py` covering all 11 routes; expanded `test_fun_plugin.py` with would-you-rather, meme, and fact command tests; new `tests/unit/plugins/fun/test_wyr_view.py` for `WouldYouRatherView`.
- **Docs**: `plugins/fun/AGENTS.md` updated to describe the real web panel (11 cards, route list) instead of calling it a placeholder.
