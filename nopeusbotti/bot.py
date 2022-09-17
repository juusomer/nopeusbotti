import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List

import paho.mqtt.client as mqtt
import tweepy
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

from nopeusbotti.plots import plot_route_to_file


@dataclass(frozen=True)
class MonitoredArea:
    north: float
    south: float
    east: float
    west: float
    speed_limit: float


@dataclass(frozen=True)
class VehicleKey:
    route_name: str
    operating_day: str
    start_time: str


class MonitoredVehicle:
    def __init__(self):
        self.max_timestamp = 0
        self.position_messages = []

    def add_position_message(self, message):
        self.max_timestamp = max(self.max_timestamp, message["tsi"])
        self.position_messages.append(message)


class InvalidCoordinateError(ValueError):
    pass


class Bot:

    MQTT_BROKER_URL = "mqtt.hsl.fi"
    ROUTE_GRAPHQL_URL = (
        "https://api.digitransit.fi/routing/v1/routers/hsl/index/graphql"
    )

    # Required message count for plots
    MESSAGE_COUNT_MIN = 10

    # Monitored vehicles with no data in this time will be dropped
    EXPIRATION_SECONDS = 60

    def __init__(self, area: MonitoredArea, routes: List[str], send_tweets: bool):
        self.max_timestamp = 0
        self.vehicles: Dict[VehicleKey, MonitoredVehicle] = {}
        self.area = area
        self.routes = routes
        self.send_tweets = send_tweets

        self.logger = logging.getLogger(__name__)

        if self.send_tweets:
            self.access_token = os.environ["ACCESS_TOKEN"]
            self.access_token_secret = os.environ["ACCESS_TOKEN_SECRET"]
            self.api_key = os.environ["API_KEY"]
            self.api_key_secret = os.environ["API_KEY_SECRET"]

    def run(self):
        if not self.send_tweets:
            self.logger.info(
                "Run with --no-tweets: only producing figures, will not send any tweets"
            )
        client = mqtt.Client()
        client.tls_set()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.connect(Bot.MQTT_BROKER_URL, 8883, 60)
        client.loop_forever()

    def on_connect(self, client, userdata, flags, rc):
        self.logger.info(f"Client connected (rc = {rc})")
        for route in self.routes:
            topic = self.get_mqtt_topic(route)
            self.logger.info(f"Subscribing to {topic}")
            client.subscribe(topic)

    @lru_cache
    def get_mqtt_topic(self, route_name: str):
        query = gql(
            f"""
            {{
                routes(name: "{route_name}", transportModes: BUS) {{
                    gtfsId
                }}
            }}
            """
        )

        transport = AIOHTTPTransport(url=Bot.ROUTE_GRAPHQL_URL)
        client = Client(transport=transport, fetch_schema_from_transport=True)
        result = client.execute(query)

        try:
            route_id = result["routes"][0]["gtfsId"].replace("HSL:", "")
        except (KeyError, IndexError, AttributeError):
            raise ValueError("No valid ID found for route {route}")

        return f"/hfp/v2/journey/ongoing/vp/+/+/+/{route_id}/#"

    def on_message(self, client, userdata, msg):
        try:
            message = json.loads(msg.payload)["VP"]
            self.max_timestamp = max(self.max_timestamp, message["tsi"])
            key = self.get_vehicle_key(msg.topic, message)

            if self.is_within_area(message):
                self.handle_vehicle_within_area(key, message)
            else:
                self.handle_vehicle_outside_area(key)

            self.remove_expired_vehicles()

        except InvalidCoordinateError:
            self.logger.debug(f"Invalid coordinates from {key} in {message}, ignoring")

        except Exception as e:
            self.logger.exception(e)

    def handle_vehicle_within_area(self, vehicle_key: VehicleKey, message: dict):
        if not vehicle_key in self.vehicles:
            self.logger.info(f"{vehicle_key} has entered the monitored area")
            self.vehicles[vehicle_key] = MonitoredVehicle()

        self.vehicles[vehicle_key].add_position_message(message)

    def handle_vehicle_outside_area(self, vehicle_key: VehicleKey):
        if vehicle_key not in self.vehicles:
            return

        position_messages = self.vehicles.pop(vehicle_key).position_messages
        route_name = vehicle_key.route_name

        if len(position_messages) <= Bot.MESSAGE_COUNT_MIN:
            raise ValueError(
                f"{vehicle_key} has only {len(position_messages)} data points"
            )

        self.logger.info(f"{vehicle_key} has left the area, plotting route")
        filename, title = plot_route_to_file(route_name, position_messages, self.area)
        self.logger.info(f"Saved plot to {filename}")

        if self.send_tweets:
            self.post_route_to_twitter(filename, title)
            self.remove_file(filename)

    def get_vehicle_key(self, topic: str, message: dict):
        route_name = self.get_route_name(topic)
        return VehicleKey(route_name, message["oday"], message["start"])

    def get_route_name(self, mqtt_topic: str):
        return mqtt_topic.split("/")[11]

    def is_within_area(self, message: dict):
        try:
            return (
                self.area.south <= message["lat"] <= self.area.north
                and self.area.west <= message["long"] <= self.area.east
            )
        except TypeError:
            # Lat / long coordinates sometimes null
            raise InvalidCoordinateError

    def remove_expired_vehicles(self):
        for key, vehicle in self.vehicles.items():
            if self.is_expired(vehicle):
                self.logger.info(f"Dropping expired data from {key}")
                self.vehicles.pop(key)

    def is_expired(self, vehicle: MonitoredVehicle):
        return self.max_timestamp - vehicle.max_timestamp >= Bot.EXPIRATION_SECONDS

    def post_route_to_twitter(self, filename: str, title: str):
        self.logger.info(f"Posting {filename} to Twitter")
        auth = tweepy.OAuthHandler(self.api_key, self.api_key_secret)
        auth.set_access_token(self.access_token, self.access_token_secret)
        api = tweepy.API(auth)
        media = api.media_upload(filename)
        client = tweepy.Client(
            consumer_key=self.api_key,
            consumer_secret=self.api_key_secret,
            access_token=self.access_token,
            access_token_secret=self.access_token_secret,
        )
        client.create_tweet(text=title, media_ids=[media.media_id])
        self.logger.info(f"Posted {filename} to Twitter")

    def remove_file(self, filename: str):
        self.logger.info(f"Removing {filename}")
        os.remove(filename)
