import io

import folium
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def plot_route_speed(route_data, speed_limit, ax=None):
    speed_km_h = route_data.set_index("time").speed * 3.6
    ax = speed_km_h.plot(style="o-", ax=ax)
    ax = speed_km_h[speed_km_h > speed_limit].plot(style="o", color="red", ax=ax)
    ax.set_ylim(bottom=0, top=max([speed_limit + 10, speed_km_h.max() + 5]))
    ax.set_xlabel("Aika")
    ax.set_ylabel("Nopeus (km/h)")
    ax.hlines(
        speed_limit,
        route_data.time.min(),
        route_data.time.max(),
        color="red",
        linestyle="dashed",
    )
    return ax


def to_png(folium_map, delay=0.1):
    crop_area = (0, 0, folium_map.width[0], folium_map.height[0])
    image = Image.open(io.BytesIO(folium_map._to_png(delay)))
    return image.crop(crop_area)


def plot_route_map(route_data, center, speed_limit, as_png=True):
    m = folium.Map(
        location=center,
        zoom_start=17,
        height=400,
        width=400,
        zoom_control=not as_png,
        control_scale=True,
    )

    coordinates = [(point.lat, point.long) for _, point in route_data.iterrows()]
    speeds = [3.6 * point.speed for _, point in route_data.iterrows()]

    folium.PolyLine(coordinates).add_to(m)

    for point, speed in zip(coordinates[:-1], speeds[:-1]):
        color = "red" if speed > speed_limit else "#3388ff"
        folium.CircleMarker(
            location=point,
            radius=1.5,
            color=color,
            fill_color=color,
            fill=True,
            fill_opacity=1,
            tooltip=f"{speed} km/h",
        ).add_to(m)

    arrow_rotation = 90 - (360 / (2 * np.pi)) * np.arctan(
        np.abs(route_data.iloc[-1].lat - route_data.iloc[-2].lat)
        / np.abs(route_data.iloc[-1].long - route_data.iloc[-2].long)
    )

    if route_data.iloc[-1].lat >= route_data.iloc[-2].lat:
        arrow_rotation += 180

    folium.RegularPolygonMarker(
        location=[route_data.iloc[-1].lat, route_data.iloc[-1].long],
        number_of_sides=3,
        radius=8,
        rotation=arrow_rotation,
        color="red" if speeds[-1] > speed_limit else "#3388ff",
        fill_color="red" if speeds[-1] > speed_limit else "#3388ff",
        fill=True,
        fill_opacity=1,
    ).add_to(m)

    return m if not as_png else to_png(m)


def plot_route_speed_and_map(route_data, area):
    width = 16
    height = width / 3
    fig, (ax1, ax2) = plt.subplots(
        1, 2, gridspec_kw={"width_ratios": [2, 1]}, figsize=(width, height)
    )
    plot_route_speed(route_data, speed_limit=area.speed_limit, ax=ax1)
    ax2.set_axis_off()
    ax2.imshow(
        plot_route_map(
            route_data,
            center=[
                (area.north + area.south) / 2,
                (area.east + area.west) / 2,
            ],
            speed_limit=area.speed_limit,
        ),
    )


def get_title(route_data, speed_limit):
    sample = route_data.iloc[0]

    route_name = sample.route_name
    route_number = sample.route_number
    time = f"{sample.operating_day} {sample.start_time}"

    overspeed = (route_data.speed * 3.6 - speed_limit).max()
    overspeed_proportional = overspeed / speed_limit

    title = title = f"Linja {route_number} ({route_name}) - lähtö {time}. "

    if overspeed >= 4:
        title += f"Suurin ylinopeus {overspeed:.1f} km/h ({100 * overspeed_proportional:.0f}%)."
    elif overspeed > 0:
        title += "Ei huomattavaa ylinopeutta."
    else:
        title += "Ei ylinopeutta."

    return title
