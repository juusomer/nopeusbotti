import uuid

import contextily as cx
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_route_to_file(route_name, position_messages, area):
    route_data = to_dataframe(position_messages)
    plot_route_speed_and_map(route_data, area)

    title = get_title(route_name, route_data, area)
    suptitle = plt.suptitle(title, y=1.02)

    plt.tight_layout()

    filename = f"{uuid.uuid4()}.png"
    plt.savefig(filename, bbox_extra_artists=(suptitle,), bbox_inches="tight")
    plt.close()

    return filename, title


def plot_route_speed_and_map(route_data, area):
    w, h = matplotlib.figure.figaspect(9 / 16)
    _, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(1.25 * w, 1.25 * h), gridspec_kw={"width_ratios": [2, 1]}
    )
    plot_route_speed(route_data, area, ax1)
    plot_route_map(route_data, area, ax2)


def plot_route_speed(route_data, area, ax):
    speed_limit = area.speed_limit
    route_data.speed.plot(style="o-", ax=ax)
    route_data.speed[route_data.speed > speed_limit].plot(style="o", color="red", ax=ax)
    ax.set_ylim(bottom=0, top=max([speed_limit + 10, route_data.speed.max() + 5]))
    ax.set_xlabel("Aika")
    ax.set_ylabel("Nopeus (km/h)")
    ax.hlines(
        speed_limit,
        route_data.index.min(),
        route_data.index.max(),
        color="red",
        linestyle="dashed",
    )


def plot_route_map(route_data, area, ax):
    ax.set_axis_off()

    speed_limit = area.speed_limit
    x = route_data.to_crs(epsg=3857).geometry.x
    y = route_data.to_crs(epsg=3857).geometry.y

    ax.plot(x, y, "o-", ms=4)
    ax.plot(
        x[route_data.speed > speed_limit],
        y[route_data.speed > speed_limit],
        "ro",
        ms=4,
    )

    arrow_x = x.iloc[-1]
    arrow_y = y.iloc[-1]
    dx = x.iloc[-1] - x.iloc[-2]
    dy = y.iloc[-1] - y.iloc[-2]
    ax.arrow(
        arrow_x + dx / 2,
        arrow_y + dy / 2,
        dx,
        dy,
        width=3,
        color="red" if route_data.iloc[-1].speed > speed_limit else "#1f77b4",
    )

    ax.margins(0.25)
    cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik, zoom=17)


def get_title(route_name, route_data, area):
    sample = route_data.iloc[0]

    route_number = sample.route_number
    time = f"{sample.operating_day} {sample.start_time}"

    overspeed = (route_data.speed - area.speed_limit).max()
    overspeed_proportional = overspeed / area.speed_limit

    title = title = f"Linja {route_number} ({route_name}) - lähtö {time}. "

    if overspeed >= 4:
        title += f"Suurin ylinopeus {overspeed:.1f} km/h ({100 * overspeed_proportional:.0f}%)."
    elif overspeed > 0:
        title += "Ei huomattavaa ylinopeutta."
    else:
        title += "Ei ylinopeutta."

    return title


def to_dataframe(position_messages):
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
    df.loc[:, "speed"] *= 3.6

    df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.long, df.lat))
    df.crs = "EPSG:4326"

    return df.set_index("time").sort_index()
