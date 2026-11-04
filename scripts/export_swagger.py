"""
Exports the REST API's Swagger spec as a static Swagger UI site (e.g. for GitHub Pages).

The spec is generated from the game config, which lists every competing robot and object id.
To keep the docs readable the config is trimmed to a few example teams and objects first.

Usage: uv run python scripts/export_swagger.py [game] [output_dir]
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.restapi.GameApi import create_api  # noqa: E402
from src.utils import read_config, game_config_path  # noqa: E402
import importlib  # noqa: E402

EXAMPLE_TEAMS = 2
EXAMPLE_OBJECTS_PER_TYPE = 4
SWAGGER_UI_VERSION = '5.17.14'

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@{version}/swagger-ui.css">
  <style>body {{ margin: 0; background: #fff; }}</style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@{version}/swagger-ui-bundle.js"></script>
  <script>
    window.ui = SwaggerUIBundle({{
      url: 'swagger.json',
      dom_id: '#swagger-ui',
      // Static docs: there is no server behind GitHub Pages, so "Try it out" is disabled
      supportedSubmitMethods: [],
    }});
  </script>
</body>
</html>
"""


def example_config(game_config: dict) -> dict:
    config = dict(game_config)
    config['robots'] = dict(list(game_config['robots'].items())[:EXAMPLE_TEAMS])

    # Keep special objects (e.g. Construction's cherry and steel) so their types appear in the example
    special_ids = {game_config[key] for key in ('cherry', 'steel') if key in game_config}
    config['objects'] = {}
    for object_type, object_ids in game_config['objects'].items():
        special = [o for o in object_ids if o in special_ids]
        others = [o for o in object_ids if o not in special_ids]
        config['objects'][object_type] = (special + others)[:EXAMPLE_OBJECTS_PER_TYPE]
    return config


def main():
    game_name = sys.argv[1] if len(sys.argv) > 1 else 'construction'
    output_dir = Path(sys.argv[2] if len(sys.argv) > 2 else 'site')

    class_name = game_name.capitalize()
    game_class = getattr(importlib.import_module(f'src.games.{game_name.lower()}.{class_name}'), class_name)
    config = example_config(read_config(game_config_path(game_name)))

    app = create_api(SimpleNamespace(GameClass=game_class, game_config=config, game_servers={}))
    spec = app.test_client().get('/swagger.json').get_json()

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'swagger.json').write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding='utf-8')
    (output_dir / 'index.html').write_text(
        INDEX_HTML.format(title=spec['info']['title'], version=SWAGGER_UI_VERSION), encoding='utf-8')
    (output_dir / '.nojekyll').touch()
    print(f'Wrote Swagger UI for {class_name} to {output_dir.resolve()}')


if __name__ == '__main__':
    main()
