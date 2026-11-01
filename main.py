# -*- coding: utf-8 -*-
import getopt
import os
import sys

from sledilnik.TrackerSetup import TrackerSetup
from src.restapi.GameApi import GameApi
from src.utils import game_config_path, tracker_config_path


def main(argv):
    tracker_config = None
    game_name = os.environ.get('GAME_NAME') or None
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
            tracker_config = arg
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

    if tracker_config is None:
        tracker_config = tracker_config_path()
    print(f'Using tracker config: {tracker_config}')

    if setup:
        TrackerSetup(tracker_config, game_config_path(game_name)).start()
    else:
        game_api = GameApi(game_name, tracker_config)
        if create_test_game:
            game_api.start_test_game_server()
        game_api.start()


def help_text():
    print("Usage:")
    print("\t--help (-h)                                     shows this help")
    print("\t--tracker-config (-t) <path to tracker config>  sets path to tracker config (default: ./config/tracker_config.yaml)")
    print("\t--setup (-s)                                    runs tracker setup")
    print("\t--game (-n) <game name>                         runs game server for given game (or set GAME_NAME)")
    print("\t--test (-d)                                     creates a test game with longer game time")


if __name__ == '__main__':
    main(sys.argv[1:])
