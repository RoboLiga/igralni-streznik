# -*- coding: utf-8 -*-
import importlib
from queue import Queue
from typing import Dict

from flask import Flask, jsonify
from flask_restx import Resource, Api, fields

from so2.servers.GameServer import GameServer
from so2.servers.StateServer import StateServer


def create_api(game_servers: Dict[str, GameServer], state_server: StateServer, tracker_config: Dict, game_config: Dict):
    app = Flask(__name__, instance_relative_config=True)
    api = Api(app,
              version='1.0',
              title='Robo liga API',
              description='A simple API for Robo Liga games.'
              )

    game_ns = api.namespace('game', description='Game operations')
    team_ns = api.namespace('team', description='Team operations')
    server_queue = Queue()

    @game_ns.route('/')
    class GameList(Resource):

        @game_ns.expect(api.model('CreateGame', {
            'team_1': fields.Integer(required=True, description='Team 1 ID'),
            'team_2': fields.Integer(required=True, description='Team 2 ID'),
        }))
        @game_ns.response(200, "Success", fields.String)
        def post(self):
            """
            Create a new game
            """
            try:
                team1Id = int(api.payload['team_1'])
                team2Id = int(api.payload['team_2'])

                GameClass = getattr(
                    importlib.import_module(f"so2.games.{game_config['game'].lower()}.{game_config['game']}"),
                    game_config['game']
                )
                new_game = GameClass(state_server, game_config, team1Id, team2Id)

                game_servers[new_game.id] = new_game
                new_game.start()

                server_queue.put(new_game.id)

                if len(game_servers) >= 50:
                    game_servers.pop(server_queue.get())

                return new_game.id

            except Exception as e:
                api.abort(500, f"Unknown error occurred: {e}")

        @game_ns.response(200, "Success", fields.List(fields.String))
        def get(self):
            """
            List all games
            """
            games = [game_id for game_id in game_servers.keys()]
            return jsonify(games)

    @game_ns.route('/<string:game_id>')
    @game_ns.response(404, 'Game not found')
    @game_ns.param('game_id', 'The game identifier')
    class Game(Resource):
        @game_ns.response(200, "Success", GameServer.to_model(api, tracker_config, game_config))
        def get(self, game_id):
            """
            Fetch a game
            """
            if game_id in game_servers:
                return game_servers[game_id].to_json()
            else:
                api.abort(404, f"Game with id {game_id} doesn't exist")

    @game_ns.route('/<string:game_id>/score')
    @game_ns.response(404, 'Game not found')
    @game_ns.param('game_id', 'The game identifier')
    class GameScore(Resource):
        alter_score_model = api.model('AlterScore', {
            'team_1': fields.Integer(required=True, description='Team 1 ID'),
            'team_2': fields.Integer(required=True, description='Team 2 ID'),
        })

        @game_ns.expect(alter_score_model)
        @game_ns.response(200, "Success", GameServer.to_model(api, tracker_config, game_config))
        def put(self, game_id):
            """
            Alter score of the game
            """
            if game_id in game_servers:
                game_server = game_servers[game_id]
                game_server.alter_score(api.payload['team_1'], api.payload['team_2'])
                return game_server.to_json()
            else:
                api.abort(404, f"Game with id {game_id} doesn't exist")

    @game_ns.route('/<string:game_id>/start')
    @game_ns.response(404, 'Game not found')
    @game_ns.param('game_id', 'The game identifier')
    class GameStart(Resource):

        @game_ns.response(200, "Success", GameServer.to_model(api, tracker_config, game_config))
        def put(self, game_id):
            """
            Start the game
            """
            if game_id in game_servers:
                game_server = game_servers[game_id]
                game_server.start_game()
                return game_server.to_json()
            else:
                api.abort(404, f"Game with id {game_id} doesn't exist")

    @game_ns.route('/<string:game_id>/stop')
    @game_ns.response(404, 'Game not found')
    @game_ns.param('game_id', 'The game identifier')
    class GameStop(Resource):
        @game_ns.response(200, "Success", GameServer.to_model(api, tracker_config, game_config))
        def put(self, game_id):
            """
            Stop the game
            """
            if game_id in game_servers:
                game_server = game_servers[game_id]
                game_server.game_on = False
                return game_server.to_json()
            else:
                api.abort(404, f"Game with id {game_id} doesn't exist")

    @game_ns.route('/<string:game_id>/time')
    @game_ns.response(404, 'Game not found')
    @game_ns.param('game_id', 'The game identifier')
    class GameTime(Resource):
        @game_ns.expect(api.model('SetTime', {
            'game_time': fields.Integer(required=True, description='Game time in seconds'),
        }))
        @game_ns.response(200, "Success", GameServer.to_model(api, tracker_config, game_config))
        def put(self, game_id):
            """
            Set game time
            """
            if game_id in game_servers:
                game_server = game_servers[game_id]
                game_server.set_game_time(api.payload['game_time'])
                return game_server.to_json()
            else:
                api.abort(404, f"Game with id {game_id} doesn't exist")

    @game_ns.route('/<string:game_id>/teams')
    @game_ns.response(404, 'Game not found')
    @game_ns.param('game_id', 'The game identifier')
    class GameTeams(Resource):
        @game_ns.expect(api.model('SetTeams', {
            'team_1': fields.Integer(required=True, description='Team 1 ID'),
            'team_2': fields.Integer(required=True, description='Team 2 ID'),
        }))
        @game_ns.response(200, "Success", GameServer.to_model(api, tracker_config, game_config))
        def put(self, game_id):
            """
            Set teams
            """
            if game_id in game_servers:
                game_server = game_servers[game_id]
                game_server.set_teams(api.payload['team_1'], api.payload['team_2'])
                return game_server.to_json()
            else:
                api.abort(404, f"Game with id {game_id} doesn't exist")

    @game_ns.route('/<string:game_id>/pause')
    @game_ns.response(404, 'Game not found')
    @game_ns.param('game_id', 'The game identifier')
    class GamePause(Resource):
        @game_ns.response(200, "Success", GameServer.to_model(api, tracker_config, game_config))
        def put(self, game_id):
            """
            Pause or unpause the game
            """
            if game_id in game_servers:
                game_server = game_servers[game_id]
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

        @team_ns.response(200, 'Success', fields.List(fields.Nested(team_model)))
        def get(self):
            """
            Get list of teams
            """
            return jsonify(
                [{"id": teamId, "name": teamName} for teamId, teamName in state_server.state.config['robots'].items()],
                ensure_ascii=False
            )

    return app
