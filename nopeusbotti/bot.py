import collections
import json
import logging
import os
from dataclasses import dataclass

import pandas as pd
import tweepy
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

from nopeusbotti.plots import plot_route_to_file


@dataclass
class Area:
    north: float
    south: float
    east: float
    west: float
    speed_limit: float


class Bot:
    def __init__(self, area, routes, send_tweets):
        self.area = area
        self.routes = routes
        self.messages = collections.defaultdict(list)
        self.send_tweets = send_tweets
        self.logger = logging.getLogger(__name__)

        if self.send_tweets:
            self.access_token = os.environ["ACCESS_TOKEN"]
            self.access_token_secret = os.environ["ACCESS_TOKEN_SECRET"]
            self.api_key = os.environ["API_KEY"]
            self.api_key_secret = os.environ["API_KEY_SECRET"]
        else:
            self.logger.info(
                "Run with --no-tweets: only producing figures, will not send any tweets"
            )

    def get_mqtt_topic(self, route):
        query = gql(
            f"""
            {{
                routes(name: "{route}", transportModes: BUS) {{
                    gtfsId
                }}
            }}
            """
        )
        transport = AIOHTTPTransport(
            url="https://api.digitransit.fi/routing/v1/routers/hsl/index/graphql"
        )
        client = Client(transport=transport, fetch_schema_from_transport=True)
        result = client.execute(query)
        try:
            route_id = result["routes"][0]["gtfsId"].replace("HSL:", "")
        except (KeyError, IndexError, AttributeError):
            raise ValueError("No valid ID found for route {route}")
        return f"/hfp/v2/journey/ongoing/vp/+/+/+/{route_id}/#"

    def get_message_key(self, message):
        return tuple(message[key] for key in ["oper", "veh", "oday", "start"])

    def get_route_name(self, mqtt_topic):
        return mqtt_topic.split("/")[11]

    def on_connect(self, client, userdata, flags, rc):
        self.logger.info(f"Client connected (rc = {rc})")
        for route in self.routes:
            topic = self.get_mqtt_topic(route)
            self.logger.info(f"Subscribing to {topic}")
            client.subscribe(topic)

    def handle_message(self, topic, message):
        key = self.get_message_key(message)

        if self.is_within_area(message):
            if not self.messages[key]:
                self.logger.info(f"{key} has entered the monitored area")
            self.messages[key].append(message)

        elif self.messages[key]:
            self.logger.info(f"{key} has left the area, plotting route")
            route_data = self.to_df(self.messages.pop(key))
            route_data = route_data.assign(route_name=self.get_route_name(topic))
            filename, title = plot_route_to_file(route_data, self.area)
            self.logger.info(f"Saved plot to {filename}")
            if self.send_tweets:
                self.post_route_to_twitter(filename, title)
                self.remove_file(filename)

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            message = json.loads(msg.payload)["VP"]
            self.handle_message(topic, message)
        except Exception as e:
            self.logger.exception(e)

    def is_within_area(self, message):
        try:
            return (
                self.area.south <= message["lat"] <= self.area.north
                and self.area.west <= message["long"] <= self.area.east
            )
        except TypeError:
            return False

    def to_df(self, position_messages):
        df = pd.DataFrame(position_messages)
        columns = {
            "desi": "route_number",
            "tst": "time",
            "spd": "speed",
            "lat": "lat",
            "long": "long",
            "oday": "operating_day",
            "start": "start_time",
        }
        df = df[columns.keys()].rename(columns=columns)
        df.loc[:, "time"] = pd.to_datetime(df.time).dt.tz_convert("EET")
        df = df.sort_values("time")
        return df

    def post_route_to_twitter(self, filename, title):
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

    def remove_file(self, filename):
        self.logger.info(f"Removing {filename}")
        os.remove(filename)
