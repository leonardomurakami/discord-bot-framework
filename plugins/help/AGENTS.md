# Help Plugin Guidelines

Canonical structure:

```
plugins/help/
├── commands/
├── models/
├── templates/
├── views/
└── web/
```

Important conventions:

- `plugin.py` exports `HelpPlugin` (re-exported via `__init__.py`). Keep command implementations on the plugin class.
- Store any reusable data helpers under `models/`. `CommandInfoManager` lives in `models/command_info.py`; extend this module or add siblings rather than creating new top-level files.
- Presentation logic and Miru views live in the `views` package. `views/embed_generators.py` houses embed builders, while interactive dropdowns sit in `views/menus.py` and are re-exported through `views/__init__.py`.
- Use `templates/` for web assets if a panel is ever added; a `.gitkeep` is present so the directory stays tracked.
- The `web/` package is available for FastAPI routes once a control panel is required.

Follow repository formatting and lint rules. Run `uv run pytest tests/unit/plugins/help` after changing behaviour.
