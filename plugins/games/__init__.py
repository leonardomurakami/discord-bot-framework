from .plugin import GamesPlugin

PLUGIN_METADATA = {
    'name': 'Games',
    'version': '1.0.0',
    'author': 'Discord Bot Framework',
    'description': 'Interactive games including enhanced trivia with scoring, achievements, and custom questions',
    'permissions': [
        'basic.games.play',
        'games.trivia.play',
        'games.trivia.manage',
        'games.admin.questions',
    ],
    'dependencies': [],
}

__all__ = ['GamesPlugin']
