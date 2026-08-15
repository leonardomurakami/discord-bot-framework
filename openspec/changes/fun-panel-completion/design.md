## Context

The fun plugin already demonstrates the framework's `WebPanelMixin` pattern with six working HTMX game cards (dice, coinflip, 8-ball, random, joke, quote) in `plugins/fun/web/routes.py` and `plugins/fun/templates/panel.html`. Each card posts to a FastAPI endpoint that returns an HTML fragment, which HTMX swaps into a `result` div. The Discord side has 11 commands across `commands/games.py` and `commands/content.py`; four of them (would-you-rather, meme, fact, choose) have no web equivalent. See proposal.md for the motivation.

The `/choose` command in `commands/games.py` (line 184-227) is missing its `permission_node` and contains a dead `len(choices) < 2` branch at line 196 — `choices` is always exactly two elements because both `option1` and `option2` are required `CommandArgument`s. The `WouldYouRatherView` in `views/__init__.py` tracks votes in two `set[int]` collections and renders ASCII progress bars; it has zero test coverage. The test file `tests/unit/plugins/fun/test_fun_plugin.py` has 26 tests covering 8 of 11 commands (missing would-you-rather, meme, fact) and zero web/view tests.

## Goals / Non-Goals

**Goals:**
- Achieve full command/panel parity: every Discord command that makes sense in a browser has a corresponding web card.
- Match the existing card pattern exactly (HTMX `hx-post` to a FastAPI route returning an HTML fragment swapped into a `.result` div) so the new cards are visually and behaviorally consistent.
- Reuse the plugin's existing `aiohttp.ClientSession`, `API_ENDPOINTS`, and `DEFAULT_*` fallback data so the web routes share the same data sources as the Discord commands.
- Fix the `/choose` command's missing permission node and remove dead code without changing its externally visible happy-path behavior.
- Close the test gaps: web routes, the three untested commands, and the view.

**Non-Goals:**
- No persistent vote storage for the web would-you-rather card — votes are client-side and ephemeral, matching the Discord view's in-memory nature.
- No authentication/authorization layer on the web panel routes beyond what the framework's `WebPanelMixin` already provides (the panel is behind Discord OAuth at the app level).
- No redesign of the existing six cards; this change only adds new cards and fixes the choose command.
- No new config fields or environment variables.

## Decisions

### Decision: Would-you-rather voting via client-side JavaScript with a server-provided question
**Choice:** The `/plugin/fun/api/wyr` GET endpoint returns an HTML fragment containing the two options and two vote buttons. Voting is handled entirely in client-side JavaScript: clicking a button increments a local counter, re-renders the results bars in the browser, and does not call back to the server. A "New question" button triggers a fresh `hx-get` to `/plugin/fun/api/wyr` to load a new random question pair.
**Rationale:** The Discord `WouldYouRatherView` stores votes in ephemeral in-memory sets that reset when the view times out. Replicating server-side vote tracking on the web would require either per-session state (the framework's Redis sessions are optional and not plugin-scoped) or a database table (the fun plugin has no models). Client-side tracking preserves the ephemeral semantics at zero infrastructure cost and keeps the route stateless. The server's only job is providing a random question, which it already does for the Discord command via `DEFAULT_WYR_QUESTIONS`.
**Alternatives considered:**
- Server-side vote tracking with a dict keyed by question: breaks under multiple workers, leaks memory, and contradicts the ephemeral design.
- A database `WYRVote` model: over-engineered for a fun feature; the fun plugin intentionally has no models.

### Decision: Meme card renders the image URL directly in an `<img>` tag
**Choice:** The `/plugin/fun/api/meme` POST endpoint fetches from the primary meme API (meme-api.com), checks the `nsfw` flag, and returns an HTML fragment with an `<img>` tag pointing to the meme `url`, plus the title, subreddit, and upvotes. If the primary API fails or returns NSFW, it falls back to the Imgflip secondary API and returns a random meme from the `data.memes` array. If both fail, it returns a friendly error fragment.
**Rationale:** The web panel can't use Discord embeds, so the image is rendered as a standard `<img>` element. The route reuses the exact same API endpoints and response-parsing logic as the Discord `random_meme` command in `commands/content.py`, ensuring parity. The NSFW check is preserved to keep the panel safe-for-work. The `basic.fun.images.view` permission node applies to the Discord command; the web panel is already gated by Discord OAuth at the app level, so no additional route-level permission check is needed (consistent with how the existing joke/quote routes work).
**Alternatives considered:**
- Downloading and re-serving the image through the bot: adds bandwidth and storage complexity for no benefit; the upstream URLs are publicly accessible.
- Skipping the NSFW check on the web: rejected — the panel should be SFW regardless of the access layer.

### Decision: Fact and meme routes share the session-guard pattern from the existing joke/quote routes
**Choice:** The fact and meme routes follow the same `if plugin.session:` guard and try/except fallback pattern already established by the `api_joke` and `api_quote` routes in `web/routes.py`. When the session is absent, the fact route falls back to `DEFAULT_FACTS` (matching the Discord command's behavior), and the meme route returns a service-unavailable message (matching the Discord command's behavior when no session exists).
**Rationale:** Consistency with the existing six routes reduces cognitive load and makes the new routes immediately familiar. The fact command's Discord version falls back to defaults when the session is missing, so the web route does the same. The meme command's Discord version returns a service-unavailable embed when there's no session, so the web route mirrors that.
**Alternatives considered:**
- Diverging from the Discord behavior (e.g., always using defaults for meme): rejected — parity is the whole point of this change.

### Decision: Choose card uses two text inputs and server-side random selection
**Choice:** The `/plugin/fun/api/choose` POST endpoint receives `option1` and `option2` from form data, validates that both are non-empty, and returns an HTML fragment with the randomly chosen option and both options listed. If either input is empty, it returns an error fragment.
**Rationale:** This mirrors the Discord command's two-argument structure exactly. Server-side selection (via `random.choice`) is consistent with all other card routes, which perform their randomness server-side. The validation replaces the Discord command's dead `len(choices) < 2` branch with a meaningful empty-input check that can actually trigger in the web form.
**Alternatives considered:**
- Client-side selection: inconsistent with the other cards and would diverge from the Discord command's `random.choice` behavior.

### Decision: Fix `/choose` by adding the permission node and removing the dead branch
**Choice:** Add `permission_node="basic.fun.games.play"` to the `@command` decorator for `choose_option` in `commands/games.py`, and remove the `if len(choices) < 2:` block (lines 196-203) since `choices` is always exactly `[option1, option2]` from the two required arguments.
**Rationale:** The permission node omission is a bug — the AGENTS.md command table already claims `/choose` uses `basic.fun.games.play`, but the code doesn't declare it. The `len(choices) < 2` check is unreachable dead code because both arguments are required; removing it improves clarity. The happy-path behavior (randomly choosing between two options) is unchanged.
**Alternatives considered:**
- Making the command accept a variable number of options instead of fixing in place: out of scope; would change the Discord command's signature and break existing usage.
- Keeping the dead branch and adding a comment: leaves misleading code that implies a validation path that can never execute.

### Decision: Web route tests use FastAPI's TestClient with a mocked plugin
**Choice:** Create `tests/unit/plugins/fun/test_fun_web_routes.py` using `starlette.testclient.TestClient` (or `httpx.AsyncClient`) with a minimal mock `FunPlugin` that provides a `render_plugin_template` stub and a mockable `session`. Each route is tested with valid input, invalid/empty input, and API-failure fallback paths. The meme and fact routes mock `plugin.session.get` to return canned API responses, mirroring the pattern in the existing command tests (`AsyncContextManager` from `tests/conftest.py`).
**Rationale:** The existing command tests already establish the `AsyncContextManager` mock pattern for `aiohttp` responses. Reusing it for web routes keeps the test style consistent. `TestClient` provides synchronous test calls against the async FastAPI app, which is simpler than spinning up a full ASGI server. The mock plugin avoids needing a real Discord bot or database.
**Alternatives considered:**
- Testing routes via direct function calls without the FastAPI test client: loses middleware/form-parsing coverage and doesn't test the actual HTTP layer.
- Using `aioresponses`/`responsesponses` library: adds a dependency; the existing `AsyncContextManager` mock pattern is sufficient and already used.

### Decision: View tests instantiate `WouldYouRatherView` directly and call callbacks with mocked `ViewContext`
**Choice:** Create `tests/unit/plugins/fun/test_wyr_view.py` that instantiates `WouldYouRatherView(option_a, option_b)`, simulates votes by directly manipulating `votes_a`/`votes_b` sets and calling `_update_results` with a mock context, and asserts on the resulting embed fields and footer text.
**Rationale:** `WouldYouRatherView` is a `miru.View` subclass whose callbacks require a `miru.ViewContext` with a Discord user and edit_response. Mocking the context is simpler than wiring a full Miru interaction loop. The vote-tracking logic (`votes_a`/`votes_b` sets, percentage calculation, bar rendering) is the behavior worth testing; the Discord plumbing around it is framework-provided.
**Alternatives considered:**
- Testing only through the command: doesn't isolate the view logic and requires mocking the entire Miru startup flow.

## Risks / Trade-offs

- **[Risk] Client-side would-you-rather votes are not shared across users** → Mitigation: this is by design (ephemeral, matching Discord). Documented in the spec scenario "Vote tracking is client-side and ephemeral." A future change could add server-side shared voting if desired.
- **[Risk] Meme API rate limits could degrade the web panel** → Mitigation: the fallback to Imgflip and the "meme gods are taking a break" message already handle total failure. The web panel is low-traffic (single-user admin tool). No additional caching in this change.
- **[Risk] Adding `permission_node` to `/choose` could lock out users who previously had access** → Mitigation: `basic.fun.games.play` is a `basic.*` node seeded as default-allow for all users by `PermissionManager.initialize()`. No guild that hasn't explicitly revoked the node will see a behavior change. The AGENTS.md already documents this node for `/choose`, so this is a fix, not a policy change.
- **[Trade-off] No persistent web vote history** → Keeps the implementation simple and consistent with the Discord view's ephemeral nature. Acceptable for a fun feature.
- **[Trade-off] Meme image is loaded directly from the upstream URL** → The bot doesn't proxy the image, so the user's browser fetches it directly from Reddit/Imgflip. This is the same behavior as opening the URL in a browser and avoids bandwidth costs on the bot host.

## Migration Plan

1. Add the four new routes to `plugins/fun/web/routes.py` and the four new cards to `plugins/fun/templates/panel.html`. These are purely additive — no existing routes or cards change.
2. Fix the `/choose` command in `plugins/fun/commands/games.py`: add `permission_node="basic.fun.games.play"` and remove the dead `len(choices) < 2` branch. The happy-path behavior is unchanged.
3. Add the new test files (`test_fun_web_routes.py`, `test_wyr_view.py`) and expand `test_fun_plugin.py` with would-you-rather, meme, and fact command tests.
4. Update `plugins/fun/AGENTS.md` to replace the "placeholder" description with accurate panel documentation.
5. Run `uv run pytest tests/unit/plugins/fun` and `uv run ruff check plugins/fun` to verify.
6. **Rollback:** revert the changes to `routes.py`, `panel.html`, `games.py`, `AGENTS.md`, and the test files. No database migration or config change is involved, so rollback is a clean git revert with no data implications.
