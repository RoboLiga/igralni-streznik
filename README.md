# Game server

This is a game server for university competition called Robo Liga FRI.

## Installation

Clone the repository and install dependencies:

```bash
uv sync
```

This installs OpenCV with GUI support (the default `gui` dependency group), which `--setup` needs.
On a headless machine, install the OpenCV build without GUI support instead:

```bash
uv sync --no-default-groups --group headless
```

## Usage

All configuration lives in the `config/` directory:

```
config/
  tracker_config.yaml       # tracker / camera settings, shared by all games
  saved_fields.pickle       # fields marked with --setup (not committed)
  <game>/game_config.yaml   # per-game settings, e.g. config/mine/game_config.yaml
```

Set the `CONFIG_DIR` environment variable to read config from a different directory with the same layout.

First, you need to edit `config/<game_name>/game_config.yaml` to your needs. Then, you need to first run:
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
uv run main.py -n GAME [-t PATH] [-s] [-d]
uv run main.py -h
```

Starts the game server for a given game, or runs interactive tracker setup to mark the game area and fields.
`-n`/`--game` is required; all other options are optional.

**Options**

| Flag | Long form          | Argument | Description                                                                                                                                     |
|------|--------------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| `-h` | `--help`           |          | Show usage information and exit.                                                                                                                |
| `-n` | `--game`           | `GAME`   | Name of the game to run (case-insensitive). **Required.** Must match a directory under `src/games` and `config`, e.g. `beach`, `example`, `mine`, `orchard`. |
| `-t` | `--tracker-config` | `PATH`   | Path to the tracker configuration YAML file. Default: `./config/tracker_config.yaml` (or `$CONFIG_DIR/tracker_config.yaml`).                                                                  |
| `-s` | `--setup`          |          | Run tracker setup instead of starting the server, to mark the game area and fields before the first run of a game.                              |
| `-d` | `--test`           |          | Start a test game (id `test`) with an extended game time. Ignored when run with `--setup`.                                                      |

**Examples**

Mark the game area and fields for `orchard` before first use:
```shell
uv run main.py --game orchard --setup
```

Run the game server for `orchard`:
```shell
uv run main.py --game orchard
```

Run a longer test game for `beach` using a custom tracker config:
```shell
uv run main.py --game beach --tracker-config ./custom_tracker.yaml --test
```

**Exit status:** `0` on success or `--help`, `1` on an invalid option, and an unhandled exception (e.g. missing `--game`) otherwise.

## Docker
To run the image with Docker make sure to set the GAME_NAME variable.

### Configuration

`docker-compose.yml` mounts the repository's `config/` directory over `/app/config`, so edits on the host
are used by the container without rebuilding the image. Put `saved_fields.pickle` in `config/` before starting:

```shell
GAME_NAME=mine docker compose up -d --build
```

Config is read at startup, so run `docker compose restart` after editing.

The image only has headless OpenCV, so `--setup` cannot run in the container. Run setup on a machine with
a display (see [Usage](#usage)) and copy the resulting `saved_fields.pickle` into `config/`.