# Music Plugin Guidelines

Plugin layout:

```
plugins/music/
├── commands/
├── models/
├── templates/
├── views/
└── web/
```

Best practices:

- `plugin.py` houses `MusicPlugin` and is re-exported via `__init__.py`. Keep Lavalink initialisation and command registration here.
- Database entities (`MusicQueue`, `MusicSession`, …) are in `models/__init__.py`. Export new models through `__all__` and register them from the plugin constructor.
- UI components live inside the `views` package: interactive Miru views in `views/__init__.py`, while FastAPI panel routes now reside in `web/routes.py`. Import the plugin with `from ..plugin import MusicPlugin` for typing support when needed.
- Command factory modules inside `commands/` should continue returning decorated callables for `_register_commands()` to attach.
- Templates for the web panel remain under `templates/`.

Follow repository formatting/lint tooling. Run focused tests with `uv run pytest tests/unit/plugins` (music tests are not yet present) and exercise integration manually when touching playback/web behaviour.
