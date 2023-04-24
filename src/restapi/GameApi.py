# -*- coding: utf-8 -*-
import importlib
import logging
from multiprocessing import freeze_support
from queue import Queue
from typing import Dict, List

from flask import Flask, jsonify
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
from flask_restx import Resource, Api, fields
from gevent.pywsgi import WSGIServer

from src.restapi.ApiError import ApiError
from src.servers.GameServer import GameServer
from src.servers.StateServer import StateServer
from src.servers.TrackerServer import TrackerServer
from src.utils import read_config, create_logger


class GameApi:
    def __init__(self, game_name: str):
        freeze_support()
        self.game_config: dict = read_config(f'./src/games/{game_name.lower()}/game_config.yaml')

        logger = create_logger('restapi.GameApi', self.game_config['log_level'])
        logger.info('Started')

        self.game_name: str = game_name.capitalize()
        self.GameClass = getattr(
            importlib.import_module(f"src.games.{self.game_name.lower()}.{self.game_name}"),
            self.game_name
        )

        self.game_servers: Dict[str, GameServer] = {}
        self.server_queue: Queue = Queue()

        self.tracker_server = TrackerServer(self.game_config)
        self.tracker_server.start()

        self.state_server: StateServer = StateServer(self.tracker_server, self.game_config)
        self.state_server.start()

        self.rest_server = WSGIServer(('0.0.0.0', 8088), create_api(self))

    def start(self):
        self.rest_server.serve_forever()

    def create_game_server(self, teams: List[int], game_id=None) -> GameServer:
        new_game = self.GameClass(self.state_server, self.game_config, teams)
        new_game.start()

        if game_id is not None:
            new_game.id = game_id

        self.server_queue.put(new_game.id)
        self.game_servers[new_game.id] = new_game

        # TODO: This needs to be changed.
        if len(self.game_servers) >= 50:
            self.game_servers.pop(self.server_queue.get())

        return new_game

    def start_test_game_server(self) -> GameServer:
        team_ids = list(self.game_config['robots'].keys())

        test_game_server = self.create_game_server(team_ids[0:2], 'test')
        test_game_server.password = 'test'
        test_game_server.game_time = 99999
        test_game_server.start_game()

        return test_game_server


def create_api(game_api: GameApi):
    app = Flask(__name__, instance_relative_config=True)
    api = Api(app,
              version='1.0',
              title='Robo liga FRI API',
              description='A simple API for Robo Liga FRI games.'
              )
    auth = HTTPBasicAuth()

    CORS(app, supports_credentials=True)

    game_ns = api.namespace('game', description='Game operations')
    team_ns = api.namespace('team', description='Team operations')

    @auth.verify_password
    def verify_password(username, password):
        if username in game_api.game_servers and game_api.game_servers.get(username).password == password:
            return username

    @game_ns.route('/')
    class GameList(Resource):

        @game_ns.expect(api.model('CreateGame', {
            'team_1': fields.Integer(required=True, description='Team 1 ID'),
            'team_2': fields.Integer(required=True, description='Team 2 ID'),
        }))
        @game_ns.response(200, "Success", api.model('GameIdPassword', {
            'game_id': fields.String(required=True, description='Game ID'),
            'password': fields.String(required=True, description='Game password')
        }))
        def post(self):
            """
            Create a new game
            """
            try:
                team_1 = int(api.payload['team_1'])
                team_2 = int(api.payload['team_2'])

                new_game = game_api.create_game_server([team_1, team_2])
                return {'game_id': new_game.id, 'password': new_game.password}

            except Exception as e:
                api.abort(500, f"Unknown error occurred: {e}")

        @game_ns.response(200, "Success", fields.List(fields.String))
        def get(self):
            """
            List all games
            """
            games = [game_id for game_id in game_api.game_servers.keys()]
            return jsonify(games)

        @auth.login_required()
        @game_ns.response(204, "Success", game_api.GameClass.to_model(api, game_api.game_config))
        def delete(self):
            """
            Delete a game
            """
            game_id = auth.username()
            if game_id in game_api.game_servers:
                return game_api.game_servers.pop(game_id, None).to_json()
            else:
                api.abort(404, f"Game with id {game_id} doesn't exist")

    @game_ns.route('/<string:game_id>')
    @game_ns.response(404, 'Game not found')
    @game_ns.param('game_id', 'The game identifier')
    class Game(Resource):
        @game_ns.response(200, "Success", game_api.GameClass.to_model(api, game_api.game_config))
        def get(self, game_id):
            """
            Fetch a game
            """
            if game_id in game_api.game_servers:
                return game_api.game_servers[game_id].to_json()
            else:
                api.abort(404, f"Game with id {game_id} doesn't exist")

    @game_ns.route('/score')
    @game_ns.response(404, 'Game not found')
    class GameScore(Resource):
        alter_score_model = api.model('AlterScore', {
            5: fields.Integer(required=True, description='Amount to add to team 5 score'),
            8: fields.Integer(required=True, description='Amount to add to team 8 score'),
        })

        @game_ns.expect(alter_score_model)
        @game_ns.response(200, "Success", game_api.GameClass.to_model(api, game_api.game_config))
        @auth.login_required()
        def put(self):
            """
            Alter score of the game
            """
            game_id = auth.username()
            if game_id in game_api.game_servers:
                game_server = game_api.game_servers[game_id]
                try:
                    game_server.alter_score(api.payload)
                except ApiError as e:
                    api.abort(e.status_code, e.message)
                return game_server.to_json()
            else:
                api.abort(404, f"Game with id {game_id} doesn't exist")

    @game_ns.route('/start')
    @game_ns.response(404, 'Game not found')
    class GameStart(Resource):

        @game_ns.response(200, "Success", game_api.GameClass.to_model(api, game_api.game_config))
        @auth.login_required()
        def put(self):
            """
            Start the game
            """
            game_id = auth.username()
            if game_id in game_api.game_servers:
                game_server = game_api.game_servers[game_id]
                game_server.start_game()
                return game_server.to_json()
            else:
                api.abort(404, f"Game with id {game_id} doesn't exist")

    @game_ns.route('/stop')
    @game_ns.response(404, 'Game not found')
    class GameStop(Resource):
        @game_ns.response(200, "Success", game_api.GameClass.to_model(api, game_api.game_config))
        @auth.login_required()
        def put(self):
            """
            Stop the game
            """
            game_id = auth.username()
            if game_id in game_api.game_servers:
                game_server = game_api.game_servers[game_id]
                game_server.stop_game()
                return game_server.to_json()
            else:
                api.abort(404, f"Game with id {game_id} doesn't exist")

    @game_ns.route('/time')
    @game_ns.response(404, 'Game not found')
    class GameTime(Resource):
        @game_ns.expect(api.model('SetTime', {
            'game_time': fields.Integer(required=True, description='Game time in seconds'),
        }))
        @game_ns.response(200, "Success", game_api.GameClass.to_model(api, game_api.game_config))
        @auth.login_required()
        def put(self):
            """
            Set game time
            """
            game_id = auth.username()
            if game_id in game_api.game_servers:
                game_server = game_api.game_servers[game_id]
                game_server.set_game_time(api.payload['game_time'])
                return game_server.to_json()
            else:
                api.abort(404, f"Game with id {game_id} doesn't exist")

    @game_ns.route('/teams')
    @game_ns.response(404, 'Game not found')
    class GameTeams(Resource):
        @game_ns.expect(api.model('SetTeams', {
            'team_1': fields.Integer(required=True, description='Team 1 ID'),
            'team_2': fields.Integer(required=True, description='Team 2 ID'),
        }))
        @game_ns.response(200, "Success", game_api.GameClass.to_model(api, game_api.game_config))
        @auth.login_required()
        def put(self):
            """
            Set teams
            """
            game_id = auth.username()
            if game_id not in game_api.game_servers:
                api.abort(404, f"Game with id {game_id} doesn't exist")

            game_server = game_api.game_servers[game_id]

            teams = [api.payload['team_1'], api.payload['team_2']]
            for team in teams:
                if team not in game_server.config['robots']:
                    api.abort(404, f"Team with id {team} doesn't exist")

            game_server.set_teams(teams)
            return game_server.to_json()

    @game_ns.route('/pause')
    @game_ns.response(404, 'Game not found')
    class GamePause(Resource):
        @game_ns.response(200, "Success", game_api.GameClass.to_model(api, game_api.game_config))
        @auth.login_required()
        def put(self):
            """
            Pause or unpause the game
            """
            game_id = auth.username()
            if game_id in game_api.game_servers:
                game_server = game_api.game_servers[game_id]
                if game_server.game_paused:
                    game_server.resume_game()
                else:
                    game_server.pause_game()

                return game_server.to_json()
            else:
                api.abort(404, f"Game with id {game_id} doesn't exist")

    @team_ns.route('/')
    class Teams(Resource):
        team_model = api.model('TeamIdName', {
            'id': fields.Integer(required=True, description='Team ID'),
            'name': fields.String(required=True, description='Team name'),
        })

        @team_ns.marshal_list_with(api.model('TeamsIdsNames', team_model), code=200)
        def get(self):
            """
            Get list of teams
            """
            testItems = [{"id": teamId, "name": teamName} for teamId, teamName in
                         game_api.game_config['robots'].items()]

            return testItems

    return app
