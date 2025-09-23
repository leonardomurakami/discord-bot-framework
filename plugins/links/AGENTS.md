# Links Plugin Guidelines

Standard layout:

```
plugins/links/
├── commands/
├── models/
├── templates/
├── views/
└── web/
```

Notes:

- `plugin.py` contains `LinksPlugin` (exported via `__init__.py`). Keep startup logic there, including database model registration.
- SQLAlchemy models are stored in `models/__init__.py`. Export new models via `__all__` and register them from the plugin class.
- No interactive views or templates yet; keep placeholders in `views/`, `web/`, and `templates/` for future use.
- Any command helpers should live in `commands/`. If you add new modules, update the plugin to attach them during initialisation.

Observe the repository lint/format configuration when editing. Run targeted tests (`uv run pytest tests/unit/plugins`) if functionality changes.
