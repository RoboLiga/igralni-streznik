# -*- coding: utf-8 -*-
import json
from queue import Queue
from typing import Dict

import orjson
from flask import Flask, request

from so2.servers.GameServer import GameServer
from so2.servers.StateServer import StateServer


def RESTAPI(game_servers: Dict[str, GameServer], state_server: StateServer):
    app = Flask(__name__, instance_relative_config=True)
    server_queue = Queue()

    @app.route("/")
    def index():
        return "{}"

    @app.route("/game/<string:game_id>", methods=["GET"])
    def game(game_id):
        if game_id in game_servers:
            return game_servers[game_id].to_json()
        else:
            return error("Igra s takšnim id-jem ne obstaja!")

    @app.route("/game", methods=["PUT"])
    def create_game():
        try:
            team1Id = int(request.json['team1'])
            team2Id = int(request.json['team2'])

            new_game = GameServer(state_server, team1Id, team2Id)
            game_servers[new_game.id] = new_game
            new_game.start()

            server_queue.put(new_game.id)

            if len(game_servers) >= 50:
                game_servers.pop(server_queue.get())

            return {"gameId": str(new_game.id)}
        except:
            return error("Prišlo je do napake!")

    @app.route("/game", methods=["GET"])
    def get_games():
        games = [str(game_id) for game_id in game_servers]
        return orjson.dumps(games)

    @app.route("/game/<string:game_id>/score", methods=["POST"])
    def alter_score(game_id):
        if game_id in game_servers:
            game_server = game_servers[game_id]
            return game_server.alter_score(request.json)
        else:
            return error("Igra s takšnim id-jem ne obstaja!")

    @app.route("/game/<string:game_id>/start", methods=["PUT"])
    def start_game(game_id):
        if game_id in game_servers:
            game_server = game_servers[game_id]
            game_server.game_data.game_on = True
            return {"gameOn": "True"}
        else:
            return error("Igra s takšnim id-jem ne obstaja!")

    @app.route("/game/<string:game_id>/stop", methods=["PUT"])
    def stop_game(game_id):
        if game_id in game_servers:
            game_server = game_servers[game_id]
            game_server.game_data.game_on = False
            return {"gameOn": "False"}
        else:
            return error("Igra s takšnim id-jem ne obstaja!")

    @app.route("/game/<string:game_id>/time", methods=["POST"])
    def set_time(game_id):
        if game_id in game_servers:
            game_server = game_servers[game_id]
            game_server.set_game_time(request.json['gameTime'])
            return {"gameTime": game_server.game_data.config.game_time}
        else:
            return error("Igra s takšnim id-jem ne obstaja!")

    @app.route("/game/<string:game_id>/teams", methods=["POST"])
    def set_teams(game_id):
        if game_id in game_servers:
            game_server = game_servers[game_id]
            game_server.set_teams(request.json['teams'])
            return request.data
        else:
            return error("Igra s takšnim id-jem ne obstaja!")

    @app.route("/teams", methods=['GET'])
    def get_teams():
        return json.dumps(
            [{"id": teamId, "name": teamName} for teamId, teamName in state_server.state.config['robots'].items()]
            , ensure_ascii=False
        ).encode('utf8')

    @app.route("/game/<string:game_id>/pause", methods=["PUT"])
    def pause_switch(game_id):
        if game_id in game_servers:
            game_server = game_servers[game_id]
            if game_server.game_data.game_on:
                game_server.pause_game()
                return {"gameOn": "False"}
            else:
                game_server.unpause_game()
                return {"gameOn": "True"}
        else:
            return error("Igra s takšnim id-jem ne obstaja!")

    @app.errorhandler(400)
    def error(msg: str):
        return msg, 400

    return app
