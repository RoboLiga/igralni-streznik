# Game server

This is a game server for university competition called Robo Liga FRI.

## Installation

Clone the repository and install dependencies:

```bash
uv sync
```

## Usage

First, you need to edit the configuration file `game_config.yaml` to your needs. Then, you need to first run:
```shell
uv run main.py --game <game_name> --setup
```
to mark the game area and fields. After that, you can run the server with:
```bash
uv run main.py --game <game_name>
```

This will start a tracker process and a server process. The tracker process will track the robots and
send their positions to the server process. The server process will expose a REST API on port `8088` for the robots
to communicate with.

### CLI reference

#### `main.py` — run the Robo Liga FRI tracker and game server

**Synopsis**

```shell
python main.py -n GAME [-t PATH] [-s] [-d]
python main.py -h
```

Starts the game server for a given game, or runs interactive tracker setup to mark the game area and fields.
`-n`/`--game` is required; all other options are optional.

**Options**

| Flag | Long form | Argument | Description |
|------|-----------|----------|--------------|
| `-h` | `--help` | | Show usage information and exit. |
| `-n` | `--game` | `GAME` | Name of the game to run (case-insensitive). **Required.** Must match a directory under `src/games`, e.g. `beach`, `example`, `mine`, `orchard`. |
| `-t` | `--tracker-config` | `PATH` | Path to the tracker configuration YAML file. Default: `./tracker_config.yaml`. |
| `-s` | `--setup` | | Run tracker setup instead of starting the server, to mark the game area and fields before the first run of a game. |
| `-d` | `--test` | | Start a test game (id `test`) with an extended game time. Ignored when run with `--setup`. |

**Examples**

Mark the game area and fields for `orchard` before first use:
```shell
python main.py --game orchard --setup
```

Run the game server for `orchard`:
```shell
python main.py --game orchard
```

Run a longer test game for `beach` using a custom tracker config:
```shell
python main.py --game beach --tracker-config ./custom_tracker.yaml --test
```

**Exit status:** `0` on success or `--help`, `1` on an invalid option, and an unhandled exception (e.g. missing `--game`) otherwise.