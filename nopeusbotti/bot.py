import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from nopeusbotti.api import hsl, twitter
from nopeusbotti.data import vehicle_positions
from nopeusbotti.plots.route import plot_route_to_file


@dataclass(frozen=True)
class Area:
    north: float
    south: float
    east: float
    west: float
    speed_limit: float


@dataclass(frozen=True)
class Vehicle:
    route_number: str
    route_name: str
    operating_day: str
    start_time: str


class VehicleData:
    def __init__(self):
        self.max_timestamp = 0
        self.position_messages: List[dict] = []

    def add_position_message(self, message):
        self.max_timestamp = max(self.max_timestamp, message["tsi"])
        self.position_messages.append(message)


class InvalidCoordinateError(ValueError):
    pass


class Bot:

    # Required message count for plots
    MESSAGE_COUNT_MIN = 10

    # Monitored vehicles with no data in this time will be dropped
    EXPIRATION_SECONDS = 60

    def __init__(
        self,
        area: Area,
        routes: List[str],
        send_tweets: bool,
        plot_directory: Path,
        write_csv: bool,
        csv_directory: Path,
    ):
        self.max_timestamp = 0
        self.vehicles: Dict[Vehicle, VehicleData] = {}
        self.area = area
        self.routes = routes
        self.send_tweets = send_tweets

        self.plot_directory = plot_directory
        self.write_csv = write_csv
        self.csv_directory = csv_directory

        self.logger = logging.getLogger(__name__)

        if self.send_tweets:
            self.twitter_credentials = twitter.Credentials.from_environment()

    def run(self):
        """Run the bot forever

        This method starts the MQTT client connection loop, which subscribes
        to the relevant topics upon connecting in Bot.on_connect and handles
        any messages consumed from them with Bot.on_message.
        """
        if not self.send_tweets:
            self.logger.info(
                "Run with --no-tweets: only producing figures, will not send any tweets"
            )

        if self.write_csv:
            self.logger.info(
                f"Run with --store-csv: producing the data used for plots to '{self.csv_directory}'"
            )
            self.create_directory(self.csv_directory)

        self.create_directory(self.plot_directory)

        hsl.process_position_messages(self.on_connect, self.on_message)

    def on_connect(self, client, userdata, flags, rc):
        """Subscribe to relevant topics upon MQTT connection"""
        self.logger.info(f"Client connected (rc = {rc})")
        for route in self.routes:
            topic = hsl.get_route_mqtt_topic(route)
            self.logger.info(f"Subscribing to {topic}")
            client.subscribe(topic)

    def on_message(self, client, userdata, msg):
        """Handle an incoming MQTT message

        This method does most of the work of the bot; it parses
        the incoming messages, checks whether they are within or
        outside the monitored area and handles them correspondingly.
        """
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

    def handle_vehicle_within_area(self, vehicle_key: Vehicle, message: dict):
        """Store a message from a vehicle inside the monitored area"""
        if not vehicle_key in self.vehicles:
            self.logger.info(f"{vehicle_key} has entered the monitored area")
            self.vehicles[vehicle_key] = VehicleData()

        self.vehicles[vehicle_key].add_position_message(message)

    def handle_vehicle_outside_area(self, vehicle_key: Vehicle):
        """Handle a message from a vehicle outside the monitored area

        This method only does something when the vehicle has just
        exited the monitored area, so a majority of the messages are
        simply ignored. In the former case we generate all the relevant
        plots, tweets and files from the data and remove the vehicle
        from the monitored vehicles.
        """
        if vehicle_key not in self.vehicles:
            return

        route_name = vehicle_key.route_name
        position_messages = self.vehicles.pop(vehicle_key).position_messages
        route_data = vehicle_positions.messages_to_dataframe(position_messages)

        if len(position_messages) <= Bot.MESSAGE_COUNT_MIN:
            raise ValueError(
                f"{vehicle_key} has only {len(position_messages)} data points"
            )

        self.logger.info(f"{vehicle_key} has left the area, plotting route")
        plot_filename = self.plot_directory / (str(uuid.uuid4()) + ".png")
        self.logger.info(f"Saving plot to {plot_filename}")
        title = plot_route_to_file(
            route_data, route_name, self.area.speed_limit, plot_filename
        )

        if self.send_tweets:
            self.logger.info(f"Sending {plot_filename} to Twitter")
            response = twitter.send_tweet(
                title, plot_filename, self.twitter_credentials
            )
            route_data = route_data.assign(tweet_id=response.data.id)
            self.remove_file(plot_filename)

        if self.write_csv:
            csv_filename = self.csv_directory / (vehicle_key.operating_day + ".csv")
            self.logger.info(f"Saving data to {csv_filename}")
            vehicle_positions.write_to_csv(route_data, csv_filename)

    def get_vehicle_key(self, topic: str, message: dict) -> Vehicle:
        route_name = self.get_route_name(topic)
        return Vehicle(message["desi"], route_name, message["oday"], message["start"])

    def get_route_name(self, mqtt_topic: str) -> str:
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
        """Remove vehicles with no data within Bot.EXPIRATION_SECONDS

        This method is called in Bot.on_message to ensure that if we
        stop receiving messages from a vehicle while it is inside
        the monitored area (whether that's due to our or its connection
        problems), we eventually free up the memory used by its data.

        The expiration is checked by comparing the most recent timestamp
        from each vehicle to the most recent timestamp of all vehicles. This
        way we do not have to care about the system clock or any possible
        delays from the MQTT broker.
        """
        for key, vehicle in self.vehicles.items():
            if self.is_expired(vehicle):
                self.logger.warn(f"Dropping expired data from {key}")
                self.vehicles.pop(key)

    def is_expired(self, vehicle: VehicleData) -> bool:
        return self.max_timestamp - vehicle.max_timestamp >= Bot.EXPIRATION_SECONDS

    def create_directory(self, directory: Path):
        self.logger.info(f"Creating directory {directory}")
        Path(directory).mkdir(parents=True, exist_ok=True)

    def remove_file(self, file_path: Path):
        self.logger.info(f"Removing file {file_path}")
        file_path.unlink()
