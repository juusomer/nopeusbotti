import collections
import datetime
import json
import logging
import os
import uuid
from dataclasses import dataclass

import matplotlib.pyplot as plt
import pandas as pd
import tweepy

from nopeusbotti.plots import get_title, plot_route_speed_and_map


@dataclass
class Area:
    north: float
    south: float
    east: float
    west: float
    speed_limit: float


class Bot:
    def __init__(self, area, stop_ids):
        self.area = area
        self.stop_ids = stop_ids
        self.messages = collections.defaultdict(list)
        self.access_token = os.environ["ACCESS_TOKEN"]
        self.access_token_secret = os.environ["ACCESS_TOKEN_SECRET"]
        self.api_key = os.environ["API_KEY"]
        self.api_key_secret = os.environ["API_KEY_SECRET"]
        self.logger = logging.getLogger(__name__)

    def get_mqtt_topic(self, stop_id):
        return f"/hfp/v2/journey/ongoing/vp/bus/+/+/+/+/+/+/{stop_id}/#"

    def get_message_key(self, message):
        return tuple(message[key] for key in ["oper", "veh", "oday", "start"])

    def get_route_name(self, mqtt_topic):
        return mqtt_topic.split("/")[11]

    def on_connect(self, client, userdata, flags, rc):
        self.logger.info(f"Client connected (rc = {rc})")
        for stop_id in self.stop_ids:
            topic = self.get_mqtt_topic(stop_id)
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
            filename, title = self.plot_route_to_file(route_data)
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
        local_timezone = (
            datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
        )
        df.loc[:, "time"] = pd.to_datetime(df.time).dt.tz_convert(local_timezone)
        df = df.sort_values("time")
        return df

    def plot_route_to_file(self, route_data):
        plot_route_speed_and_map(route_data, self.area)
        title = get_title(route_data, self.area.speed_limit)
        plt.suptitle(title)
        filename = f"{uuid.uuid4()}.png"
        plt.savefig(filename)
        self.logger.info(f"Plotted route to {filename}")
        return filename, title

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
