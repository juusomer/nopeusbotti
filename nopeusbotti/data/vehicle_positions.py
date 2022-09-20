from pathlib import Path
from typing import List

import geopandas as gpd
import pandas as pd


def messages_to_dataframe(position_messages: List[dict]) -> gpd.GeoDataFrame:
    df = pd.DataFrame(position_messages)

    columns = {
        "desi": "route_number",
        "dir": "direction",
        "oper": "operator",
        "veh": "vehicle_number",
        "tst": "time",
        "spd": "speed",
        "hdg": "heading_direction",
        "lat": "lat",
        "long": "long",
        "acc": "acceleration",
        "dl": "schedule_offset",
        "odo": "odometer_reading",
        "drst": "door_status",
        "oday": "operating_day",
        "start": "start_time",
        "stop": "stop",
    }

    df = df[columns.keys()].rename(columns=columns)
    df.loc[:, "time"] = pd.to_datetime(df.time).dt.tz_convert("EET")
    df.loc[:, "speed"] *= 3.6

    df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.long, df.lat))
    df.crs = "EPSG:4326"

    return df.set_index("time").sort_index()


def write_to_csv(df: gpd.GeoDataFrame, path: Path):
    df.drop("geometry", axis=1).to_csv(path, mode="a", header=not path.exists())


def read_from_csv(*paths: Path):
    df = pd.concat(pd.read_csv(path) for path in paths)
    df.loc[:, "time"] = pd.to_datetime(df.time)
    df.loc[:, "route_number"] = df.route_number.astype(str)
    df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.long, df.lat))
    df.crs = "EPSG:4326"
    return df.set_index("time").sort_index()
