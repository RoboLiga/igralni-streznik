from pathlib import Path
from types import SimpleNamespace

import pytest
from sledilnik.classes.Field import Field
from sledilnik.classes.Point import Point

from src.classes.StateLiveData import StateLiveData
from src.games.construction.Construction import Construction
from src.utils import read_config, check_if_object_in_area

BUILDER_ID = 0
GREEN_ID = 5
CHERRY_ID = 10
PINE_ID = 24
STEEL_ID = 9
BRICK_ID = 22

CONFIG_PATH = Path(__file__).parents[3] / 'src' / 'games' / 'construction' / 'game_config.yaml'


def rect(x0, y0, x1, y1) -> Field:
    return Field(top_left=Point(x0, y0), top_right=Point(x1, y0),
                 bottom_right=Point(x1, y1), bottom_left=Point(x0, y1))


def tracked(x, y):
    return SimpleNamespace(position=Point(x, y))


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def config():
    game_config = read_config(CONFIG_PATH)
    # Robot ids change with every competition's team list, so tests use their own
    game_config['robots'] = {BUILDER_ID: 'Builder', GREEN_ID: 'Green'}
    return game_config


@pytest.fixture
def clock(monkeypatch):
    fake_clock = FakeClock()
    monkeypatch.setattr('src.games.construction.Construction.time.time', fake_clock)
    return fake_clock


@pytest.fixture
def game(config, clock, tmp_path, monkeypatch):
    # create_logger writes game-server.log into the working directory
    monkeypatch.chdir(tmp_path)

    state = StateLiveData(config)
    # 5x4 grid of 100x100 tree fields, construction site to the right of the game field
    state.fields = {
        'game_field': rect(0, 0, 500, 400),
        'construction_site': rect(600, 0, 700, 100),
    }
    state.robots = {BUILDER_ID: tracked(-50, -50), GREEN_ID: tracked(-50, -50)}
    state.objects = {
        'trees': {CHERRY_ID: tracked(50, 50), PINE_ID: tracked(150, 50)},
        'construction_material': {STEEL_ID: tracked(800, 300), BRICK_ID: tracked(800, 300)},
    }

    construction = Construction(SimpleNamespace(state=state), config, [BUILDER_ID, GREEN_ID])
    construction.state_data = state
    construction.cherry = CHERRY_ID
    construction.steel = STEEL_ID
    return construction


def builder(game):
    return game.teams[BUILDER_ID]


def green(game):
    return game.teams[GREEN_ID]


def plant_trees(game, clock, config):
    game.update_game_state()
    clock.advance(config['plant_min_time_seconds'] + 1)
    game.update_game_state()


def test_first_team_is_builder(game):
    assert builder(game).is_builder()
    assert not green(game).is_builder()


def test_objects_with_types_reveal_cherry_and_steel(game, config):
    objects_with_types = game.get_objects_with_types()
    for tree_id in config['objects']['trees']:
        assert objects_with_types[str(tree_id)] == ('cherry' if tree_id == CHERRY_ID else 'pine')
    for material_id in config['objects']['construction_material']:
        assert objects_with_types[str(material_id)] == ('steel' if material_id == STEEL_ID else 'brick')
    assert len(objects_with_types) == sum(len(ids) for ids in config['objects'].values())


def test_tree_fields_cover_game_field(game, config):
    game.update_game_state()
    rows, cols = config['tree_fields']['rows'], config['tree_fields']['columns']
    assert len(game.tree_fields) == rows * cols
    cell = game.tree_fields['game_field_1_2']
    assert check_if_object_in_area(Point(250, 150), cell)
    assert not check_if_object_in_area(Point(150, 150), cell)


def test_tree_fields_in_json(game, config):
    game.update_game_state()
    # Tracked stand-ins can't be serialized, only fields are checked here
    game.state_data.robots, game.state_data.objects, game.state_data.timestamp = {}, {}, 0
    json_fields = game.to_json()['fields']
    rows, cols = config['tree_fields']['rows'], config['tree_fields']['columns']
    assert set(json_fields) == {'game_field', 'construction_site'} | {
        f'game_field_{row}_{col}' for row in range(rows) for col in range(cols)}
    assert json_fields['game_field_1_2'] == game.tree_fields['game_field_1_2'].to_json()


def test_tree_fields_in_model(config):
    from flask_restx import Api
    model_fields = Construction.to_model(Api(), config)['fields'].nested
    assert 'game_field_0_0' in model_fields
    assert f"game_field_{config['tree_fields']['rows'] - 1}_{config['tree_fields']['columns'] - 1}" in model_fields
    assert set(config['fields_names']) <= set(model_fields)


def test_tree_not_planted_before_min_time(game, clock, config):
    game.update_game_state()
    clock.advance(config['plant_min_time_seconds'] - 1)
    game.update_game_state()
    assert game.planted_trees == {}
    assert green(game).score == 0


def test_still_trees_get_planted_and_scored(game, clock, config):
    plant_trees(game, clock, config)
    assert set(game.planted_trees) == {CHERRY_ID, PINE_ID}
    assert green(game).score == config['points']['cherry'] + config['points']['pine']


def test_planted_tree_scores_only_once_across_ticks(game, clock, config):
    plant_trees(game, clock, config)
    score = green(game).score
    for _ in range(5):
        clock.advance(1)
        game.update_game_state()
    assert green(game).score == score


def test_small_jitter_does_not_reset_tree(game, clock, config):
    game.update_game_state()
    jitter = config['plant_min_distance_moved'] - 1
    game.state_data.objects['trees'][PINE_ID] = tracked(150 + jitter, 50)
    clock.advance(config['plant_min_time_seconds'] + 1)
    game.update_game_state()
    assert PINE_ID in game.planted_trees


def test_moving_tree_unplants_it(game, clock, config):
    plant_trees(game, clock, config)
    game.state_data.objects['trees'][PINE_ID] = tracked(350, 250)
    game.update_game_state()
    assert PINE_ID not in game.planted_trees


def test_replanted_tree_does_not_score_again(game, clock, config):
    plant_trees(game, clock, config)
    score = green(game).score
    game.state_data.objects['trees'][PINE_ID] = tracked(350, 250)
    game.update_game_state()
    clock.advance(config['plant_min_time_seconds'] + 1)
    game.update_game_state()
    assert PINE_ID in game.planted_trees
    assert green(game).score == score


def test_running_over_trees_penalizes_builder(game, clock, config):
    plant_trees(game, clock, config)
    game.state_data.robots[BUILDER_ID] = tracked(60, 60)
    game.update_game_state()
    assert CHERRY_ID not in game.planted_trees
    assert PINE_ID in game.planted_trees
    assert builder(game).score == -config['points']['cherry']

    game.state_data.robots[BUILDER_ID] = tracked(160, 60)
    game.update_game_state()
    assert game.planted_trees == {}
    assert builder(game).score == -config['points']['cherry'] - config['points']['pine']


def test_ran_over_tree_can_be_replanted(game, clock, config):
    plant_trees(game, clock, config)
    game.state_data.robots[BUILDER_ID] = tracked(160, 60)
    game.update_game_state()
    game.state_data.robots[BUILDER_ID] = tracked(-50, -50)
    clock.advance(config['plant_min_time_seconds'] + 1)
    game.update_game_state()
    assert PINE_ID in game.planted_trees


def test_missing_builder_does_not_crash(game, clock, config):
    plant_trees(game, clock, config)
    del game.state_data.robots[BUILDER_ID]
    game.update_game_state()
    assert set(game.planted_trees) == {CHERRY_ID, PINE_ID}
    assert builder(game).score == 0


def test_tree_seen_after_start_is_tracked(game, clock, config):
    game.update_game_state()
    game.state_data.objects['trees'][30] = tracked(250, 250)
    game.update_game_state()
    clock.advance(config['plant_min_time_seconds'] + 1)
    game.update_game_state()
    assert 30 in game.planted_trees


def test_delivered_materials_score(game, config):
    game.update_game_state()
    assert builder(game).score == 0

    game.state_data.objects['construction_material'][STEEL_ID] = tracked(650, 50)
    game.update_game_state()
    assert builder(game).score == config['points']['steel']

    game.state_data.objects['construction_material'][BRICK_ID] = tracked(620, 80)
    game.update_game_state()
    assert builder(game).score == config['points']['steel'] + config['points']['brick']

    game.state_data.objects['construction_material'][STEEL_ID] = tracked(800, 300)
    game.update_game_state()
    assert builder(game).score == config['points']['brick']


def test_builder_score_combines_materials_and_penalties(game, clock, config):
    plant_trees(game, clock, config)
    game.state_data.objects['construction_material'][STEEL_ID] = tracked(650, 50)
    game.state_data.robots[BUILDER_ID] = tracked(160, 60)
    game.update_game_state()
    assert builder(game).score == config['points']['steel'] - config['points']['pine']
