import logging

import click
import matplotlib
import matplotlib.pyplot as plt
import paho.mqtt.client as mqtt
from gql.transport.aiohttp import log as gql_logger

from nopeusbotti.bot import Area, Bot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
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
    "--log-only",
    help="If set, do not create and store images, do not tweet, only log the line, time, date, maximum speed and speed limit. Includes --no-tweets.",
    is_flag=True,
    default=False,
)
def main(north, south, east, west, speed_limit, route, no_tweets, log_only):
    if log_only:
        no_tweets = True
    area = Area(north, south, east, west, speed_limit)
    bot = Bot(area, route, send_tweets=not no_tweets, log_only=log_only)
    client = mqtt.Client()
    client.tls_set()
    client.on_connect = bot.on_connect
    client.on_message = bot.on_message
    client.connect("mqtt.hsl.fi", 8883, 60)
    client.loop_forever()


if __name__ == "__main__":
    main()
