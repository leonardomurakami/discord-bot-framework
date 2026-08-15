## 1. Fix `/choose` command

- [x] 1.1 Add `permission_node="basic.fun.games.play"` to the `@command` decorator for `choose_option` in `plugins/fun/commands/games.py` (currently missing at line 184-191).
- [x] 1.2 Remove the dead `if len(choices) < 2:` validation branch (lines 196-203) in `choose_option` since `choices` is always exactly `[option1, option2]` from the two required arguments.
- [x] 1.3 Verify the existing `test_choose_command` and `test_choose_command_error` tests still pass after the permission node addition and dead-code removal.

## 2. Web panel routes — would-you-rather

- [x] 2.1 Add a `GET /plugin/fun/api/wyr` endpoint to `plugins/fun/web/routes.py` that randomly selects a question pair from `DEFAULT_WYR_QUESTIONS` and returns an HTML fragment with both options and two vote buttons (A/B).
- [x] 2.2 Implement client-side vote tracking JavaScript in the would-you-rather card: clicking a button increments a local counter, renders live results bars (percentage split + vote counts), and does not call back to the server. Include a "New question" button that triggers `hx-get` to reload a fresh question.

## 3. Web panel routes — meme

- [x] 3.1 Add a `POST /plugin/fun/api/meme` endpoint to `plugins/fun/web/routes.py` that fetches from the primary meme API (`API_ENDPOINTS["meme_primary"]`), checks the `nsfw` flag, and returns an HTML fragment with an `<img>` tag, title, subreddit, and upvotes.
- [x] 3.2 Add Imgflip fallback to the meme endpoint: if the primary API fails or returns NSFW, fetch from `API_ENDPOINTS["meme_secondary"]`, pick a random meme from `data.memes`, and return an HTML fragment with the image and name.
- [x] 3.3 Add the "all APIs fail" and "no session" error paths to the meme endpoint, returning a friendly "meme gods are taking a break" or service-unavailable HTML fragment respectively.

## 4. Web panel routes — fact

- [x] 4.1 Add a `POST /plugin/fun/api/fact` endpoint to `plugins/fun/web/routes.py` that fetches from `API_ENDPOINTS["fact"]` when `plugin.session` is available, parses the `text` field, and returns an HTML fragment with the fact and an educational emoji.
- [x] 4.2 Add the fallback path: if the API fails or `plugin.session` is None, randomly select from `DEFAULT_FACTS` and return the HTML fragment.

## 5. Web panel routes — choose

- [x] 5.1 Add a `POST /plugin/fun/api/choose` endpoint to `plugins/fun/web/routes.py` that receives `option1` and `option2` from form data, validates both are non-empty, and returns an HTML fragment with the randomly chosen option and both options listed.
- [x] 5.2 Add the empty-input error path: if either option is empty/whitespace-only, return an error HTML fragment requesting both options.

## 6. Web panel template

- [x] 6.1 Add the would-you-rather card to `plugins/fun/templates/panel.html` inside the `.game-grid`: a card with the question display area, A/B vote buttons, a results area, and a "New question" button. Wire the initial load to `hx-get="/plugin/fun/api/wyr"`.
- [x] 6.2 Add the meme card to `panel.html`: a "Get new meme" button that posts to `/plugin/fun/api/meme` and swaps the result into a `.result` div, following the existing card pattern.
- [x] 6.3 Add the fact card to `panel.html`: a "Get a fact" button that posts to `/plugin/fun/api/fact` and swaps the result into a `.result` div.
- [x] 6.4 Add the choose card to `panel.html`: a form with two text inputs (`option1`, `option2`) and a "Choose for me" submit button that posts to `/plugin/fun/api/choose` and swaps the result into a `.result` div.
- [x] 6.5 Add any card-specific CSS to the `{% block extra_styles %}` section (e.g., vote bar styling for would-you-rather, image sizing for meme) consistent with the existing `.game-card` pattern.

## 7. Command tests — would-you-rather, meme, fact

- [x] 7.1 Add a test for the would-you-rather command with a mocked Miru client: assert the command responds with an embed containing both options and calls `miru_client.start_view`.
- [x] 7.2 Add a test for the would-you-rather command without a Miru client (`plugin.bot.miru_client` is None): assert the command responds with the embed only and does not attempt to start a view.
- [x] 7.3 Add a test for the meme command with primary API success: mock `plugin.session.get` to return a non-NSFW meme response and assert the embed contains the image URL.
- [x] 7.4 Add a test for the meme command with primary API failure/NSFW falling back to Imgflip: mock the primary response to fail or be NSFW and the secondary to return a valid memes array, assert the embed contains the Imgflip meme image.
- [x] 7.5 Add a test for the meme command with no session: assert it responds with a service-unavailable embed.
- [x] 7.6 Add a test for the fact command with API success: mock `plugin.session.get` to return a valid fact and assert the embed contains the fact text.
- [x] 7.7 Add a test for the fact command with API failure falling back to `DEFAULT_FACTS`: mock the session to raise and assert the embed contains a default fact.

## 8. Web panel route tests

- [x] 8.1 Create `tests/unit/plugins/fun/test_fun_web_routes.py` with a test fixture that builds a FastAPI app via `register_fun_routes` using a mock `FunPlugin` (stubbed `render_plugin_template` and mockable `session`).
- [x] 8.2 Add tests for the existing dice route: valid notation, invalid format, out-of-range dice/sides.
- [x] 8.3 Add tests for the existing coinflip and 8-ball routes: coinflip returns a result; 8-ball with a question returns an answer, 8-ball with empty question returns an error.
- [x] 8.4 Add tests for the existing random route: valid range, min > max error, range too large error.
- [x] 8.5 Add tests for the existing joke and quote routes: API success path and API-failure fallback path (mock `plugin.session.get`).
- [x] 8.6 Add a test that the main panel page (`GET /plugin/fun`) returns an HTML response containing all game cards.
- [x] 8.7 Add tests for the new would-you-rather route: `GET /plugin/fun/api/wyr` returns an HTML fragment containing both options and vote buttons.
- [x] 8.8 Add tests for the new meme route: primary API success (non-NSFW), primary NSFW fallback to Imgflip, all APIs fail, no session.
- [x] 8.9 Add tests for the new fact route: API success, API failure fallback to `DEFAULT_FACTS`, no session fallback.
- [x] 8.10 Add tests for the new choose route: two valid options returns a choice, empty option returns an error.

## 9. Would-You-Rather view tests

- [x] 9.1 Create `tests/unit/plugins/fun/test_wyr_view.py` with a test that instantiates `WouldYouRatherView("optA", "optB")` and asserts the two buttons are present with correct labels/emojis.
- [x] 9.2 Add a test simulating a vote for option A: add a user id to `votes_a`, call `_update_results` with a mock context, and assert the embed fields show option A at 100% with 1 total vote.
- [x] 9.3 Add a test for mixed votes (3 for A, 1 for B): assert the results show 75.0% / 25.0% with 4 total votes.
- [x] 9.4 Add a test for the toggle-off behavior: a user in `votes_a` who votes A again is removed from `votes_a`, and the results update to zero total votes with equal percentages.

## 10. Documentation and validation

- [x] 10.1 Update `plugins/fun/AGENTS.md`: remove the "currently a placeholder for future expansion" claim in the Architecture section and replace with an accurate description of the web panel (11 interactive HTMX cards covering all commands, route list).
- [x] 10.2 Update the `plugins/fun/AGENTS.md` Overview section to mention the web panel provides full command/panel parity instead of "can surface high scores or activity metrics."
- [x] 10.3 Run `uv run pytest tests/unit/plugins/fun` and ensure all tests pass with coverage at or above the project's 70% threshold.
- [x] 10.4 Run `uv run ruff check plugins/fun` and `uv run black --check plugins/fun` (135 char line length); fix any findings.
