# Admin Plugin Guidelines

This plugin now follows the shared layout used by every plugin:

```
plugins/admin/
├── commands/
├── models/
├── templates/
├── views/
└── web/
```

Key notes for future changes:

- Keep the main plugin class in `plugin.py` and expose it from `__init__.py`.
- Slash/prefix command factories belong in `commands/`; the existing helpers return decorated callables that get attached during plugin initialisation.
- Miru UI classes live inside the `views` package. FastAPI web panel routes now live in `web/routes.py` and may import the plugin via `from ..plugin import AdminPlugin` for type hints.
- The admin plugin currently has no bespoke database tables. If you introduce any, add them to `models/__init__.py` and remember to register them in `plugin.py`.
- Templates used by the FastAPI panel should live under `templates/`.

Follow the repository-wide formatting and lint rules (Black 135, Ruff). Run the plugin tests with `uv run pytest tests/unit/plugins/admin` when touching behaviour.
