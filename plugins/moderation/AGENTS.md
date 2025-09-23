# Moderation Plugin Guidelines

Directory contract:

```
plugins/moderation/
├── commands/
├── models/
├── templates/
├── views/
└── web/
```

Guidance:

- Keep the plugin entry point in `plugin.py` and export it from `__init__.py`.
- Command factory modules inside `commands/` should return decorated callables ready to be attached in `_register_commands()`.
- Miru views (none currently) belong in the `views` package; add modules there if UI components are added.
- Place any future SQLAlchemy models in `models/__init__.py` and register them from `plugin.py`.
- Web panel assets should live under `templates/` if introduced, with HTTP handlers defined under `web/`.

Use repo-standard formatting/linting. Execute `uv run pytest tests/unit/plugins/moderation` when altering behaviour.
