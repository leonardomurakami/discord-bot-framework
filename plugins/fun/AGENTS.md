# Fun Plugin Guidelines

Layout mirror for all plugins:

```
plugins/fun/
├── commands/
├── models/
├── templates/
├── views/
└── web/
```

Pointers:

- `plugin.py` holds `FunPlugin` and remains the entry point exposed via `__init__.py`.
- Command factory helpers in `commands/` attach decorated coroutine functions to the plugin; extend those modules when adding new commands so registration happens through `_register_commands()`.
- Miru trivia and mini-game views belong in `views/__init__.py`. Keep shared presentation helpers alongside them if needed.
- FastAPI panel routes live in `web/routes.py`; call `register_fun_routes()` from the plugin's `register_web_routes()` implementation.
- The plugin does not yet persist data; add future models to `models/__init__.py` and remember to register them from `FunPlugin`.
- Web assets for the panel live in `templates/`.

Adhere to repo formatting/linting. When touching behaviour run `uv run pytest tests/unit/plugins/fun`.
