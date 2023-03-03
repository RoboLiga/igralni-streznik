# Game server

This is a game server for university competition called Robo Liga FRI.

## Installation

Clone the repository and install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

First, you need to edit the configuration file `game_config.yaml` to your needs. Then, you need to first run:
```shell
python main.py --game <game_name> --setup
```
to mark the game area and fields. After that, you can run the server with:
```bash
python main.py --game <game_name>
```

This will start a tracker process and a server process. The tracker process will track the robots and
send their positions to the server process. The server process will expose a REST API on port `8088` for the robots
to communicate with.