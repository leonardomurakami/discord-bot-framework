# Utility Plugin Guidelines

Shared layout:

```
plugins/utility/
├── commands/
├── models/
├── templates/
├── views/
└── web/
```

Recommendations:

- `plugin.py` exports `UtilityPlugin` (via `__init__.py`). Keep aiohttp session management and command registration here.
- Command factory modules in `commands/` should continue returning decorated callables; `_register_commands()` attaches them.
- Place future Miru components under `views/` and new persistence models under `models/`.
- The templates directory is ready for any future web panel assets, and `web/` should hold FastAPI routes when needed.

Respect repository-wide lint/format tooling. Run `uv run pytest tests/unit/plugins/utility` when altering behaviour.
