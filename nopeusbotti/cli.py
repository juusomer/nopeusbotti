import logging
from pathlib import Path

import click
import matplotlib
import matplotlib.pyplot as plt
from gql.transport.aiohttp import log as gql_logger

from nopeusbotti.bot import Area, Bot

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
gql_logger.setLevel(logging.WARNING)

matplotlib.use("Agg")
plt.style.use("seaborn-darkgrid")


@click.command()
@click.option(
    "--north",
    help="The northernmost latitude coordinate (EPSG:4326 / WGS84) of the monitored area",
    type=float,
    required=True,
)
@click.option(
    "--south",
    help="The southernmost latitude coordinate (EPSG:4326 / WGS84) of the monitored area",
    type=float,
    required=True,
)
@click.option(
    "--east",
    help="The easternmost longitude coordinate  (EPSG:4326 / WGS84) of the monitored area",
    type=float,
    required=True,
)
@click.option(
    "--west",
    help="The westernmost longitude coordinate  (EPSG:4326 / WGS84) of the monitored area",
    type=float,
    required=True,
)
@click.option(
    "--speed-limit",
    help="Speed limit withing the monitored area",
    type=float,
    required=True,
)
@click.option(
    "--route",
    help="The routes to track. This option can be repeated as many times as needed.",
    multiple=True,
    required=True,
)
@click.option(
    "--no-tweets",
    help="If set, do not send any tweets, only produce the figures (for testing purposes).",
    is_flag=True,
    default=False,
)
@click.option(
    "--plot-directory",
    help="The directory for storing the plotted figures. Unless --no-tweets is specified, the figures are only stored here temporarily before publishing to twitter.",
    default="plots",
)
@click.option(
    "--write-csv",
    help="If set, the data used to draw each plot will be written in the specified directory (--csv-directory)",
    is_flag=True,
    default=False,
)
@click.option(
    "--csv-directory",
    help="The directory for storing the data if --store-csv is specified",
    default="data",
)
def main(
    north,
    south,
    east,
    west,
    speed_limit,
    route,
    no_tweets,
    plot_directory,
    write_csv,
    csv_directory,
):
    bot = Bot(
        area=Area(north, south, east, west, speed_limit),
        routes=route,
        send_tweets=not no_tweets,
        plot_directory=Path(plot_directory),
        write_csv=write_csv,
        csv_directory=Path(csv_directory),
    )
    bot.run()


if __name__ == "__main__":
    main()
