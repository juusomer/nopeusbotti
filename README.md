# nopeusbotti

A Twitter bot that plots the velocities of HSL buses.

# Installation

This project uses Poetry for dependency management. Please refer to their documentation on how to install it: https://python-poetry.org/docs/#installation. The required Python version is >= 3.8.

After installing Poetry, simply run

```bash
poetry install
```

to install all the dependencies in a virtualenv.

# Running

After installing the dependencies, the bot can be run with

```
poetry run nopeusbotti [OPTIONS]

Options:
  --north FLOAT        The northernmost latitude coordinate of the monitored
                       area  [required]
  --south FLOAT        The southernmost latitude coordinate of the monitored
                       area  [required]
  --east FLOAT         The easternmost longitude coordinate of the monitored
                       area  [required]
  --west FLOAT         The westernmost longitude coordinate of the monitored
                       area  [required]
  --speed-limit FLOAT  Speed limit withing the monitored area  [required]
  --route TEXT         The routes to track. This option can be repeated as
                       many times as needed.  [required]
  --no-tweets          If set, do not send any tweets, only produce the
                       figures (for testing purposes).
  --help               Show this message and exit.
```

Unless `--no-tweets` is set, the following Twitter API credentials must be provided as environment variables:
- `ACCESS_TOKEN`
- `ACCESS_TOKEN_SECRET`
- `API_KEY`
- `API_KEY_SECRET`

The "Essential" access category is sufficient to run the bot: API v1.1 is used for posting the images, and v2 for the actual tweets. See https://developer.twitter.com/en/portal/petition/essential/basic-info for more information.

The bot tracks buses within an area defined by maximum and minimum lat/long values. The buses are defined with the route numbers, e.g. `570`.

The following command

```bash
poetry run nopeusbotti \
  --speed-limit 30 \
  --north 60.297449 --south 60.2958756 --east 25.059465 --west 25.0569888 \
  --route 570 --route 711 --route 717 --route 717K
```

runs the bot as seen on https://twitter.com/30bussit:

- the monitored routes are 570, 711, 717 and 717K
- the speed limit is 30
- the speed limit is monitored within the depicted area:

![An example of monitored area](/img/area.PNG)