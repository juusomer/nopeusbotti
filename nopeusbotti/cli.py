import logging

import click
import matplotlib
import matplotlib.pyplot as plt
import paho.mqtt.client as mqtt

from nopeusbotti.bot import Area, Bot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

matplotlib.use("Agg")
plt.style.use("seaborn-darkgrid")


@click.command()
@click.option(
    "--north",
    help="The northernmost latitude coordinate of the monitored area",
    type=float,
    required=True,
)
@click.option(
    "--south",
    help="The southernmost latitude coordinate of the monitored area",
    type=float,
    required=True,
)
@click.option(
    "--east",
    help="The easternmost longitude coordinate of the monitored area",
    type=float,
    required=True,
)
@click.option(
    "--west",
    help="The westernmost longitude coordinate of the monitored area",
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
    "--stop-id",
    help="The stops ids to track. This option can be repeated as many times as needed.",
    multiple=True,
    required=True,
)
def main(north, south, east, west, speed_limit, stop_id):
    area = Area(north, south, east, west, speed_limit)
    bot = Bot(area, stop_id)
    client = mqtt.Client()
    client.tls_set()
    client.on_connect = bot.on_connect
    client.on_message = bot.on_message
    client.connect("mqtt.hsl.fi", 8883, 60)
    client.loop_forever()


if __name__ == "__main__":
    main()
