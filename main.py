# -*- coding: utf-8 -*-
import getopt
import sys

from sledilnik.TrackerSetup import TrackerSetup
from src.restapi.GameApi import GameApi


def main(argv):
    tracker_config_path = './tracker_config.yaml'
    game_name = None
    setup = False
    create_test_game = False

    try:
        opts, args = getopt.getopt(
            argv,
            "ht:g:sn:d",
            [
                "help",
                "tracker-config=",
                "setup",
                "game=",
                "test"
            ]
        )
    except getopt.GetoptError:
        help_text()
        sys.exit(1)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            help_text()
            sys.exit()
        elif opt in ("-t", "--tracker-config"):
            print(f'Tracker config path: {arg}')
            tracker_config_path = arg
        elif opt in ("-s", "--setup"):
            print('Running tracker setup')
            setup = True
        elif opt in ("-n", "--game"):
            print(f'Game name: {arg}')
            game_name = arg
        elif opt in ("-d", "--test"):
            print('Creating a game with id "test"')
            create_test_game = True

    if game_name is None:
        raise Exception("Game name not specified.")

    if setup:
        TrackerSetup(tracker_config_path, f'./src/games/{game_name.lower()}/game_config.yaml').start()
    else:
        game_api = GameApi(game_name)
        if create_test_game:
            game_api.start_test_game_server()
        game_api.start()


def help_text():
    print("Usage:")
    print("\t--help (-h)                                     shows this help")
    print("\t--tracker-config (-t) <path to tracker config>  sets path to tracker config")
    print("\t--setup (-s)                                    runs tracker setup")
    print("\t--game (-n) <game name>                         runs game server for given game")
    print("\t--test (-d)                                     creates a test game with longer game time")


if __name__ == '__main__':
    main(sys.argv[1:])
