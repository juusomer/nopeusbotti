import contextily as cx
import matplotlib
import matplotlib.pyplot as plt

from nopeusbotti.data import constants


def plot_route_to_file(route_data, route_name, speed_limit, path):
    plot_route_speed_and_map(route_data, speed_limit)

    sample = route_data.iloc[0]
    route_number = sample.route_number
    time = f"{sample.operating_day} {sample.start_time}"

    speeding = (route_data.speed - speed_limit).max()
    speeding_proportional = speeding / speed_limit

    title = title = f"Linja {route_number} ({route_name}) - lähtö {time}. "

    if speeding >= constants.SPEEDING_THRESHOLD:
        title += f"Suurin ylinopeus {speeding:.1f} km/h ({100 * speeding_proportional:.0f}%)."
    elif speeding > 0:
        title += "Ei huomattavaa ylinopeutta."
    else:
        title += "Ei ylinopeutta."

    plt.suptitle(title, y=0.9)
    plt.savefig(path)
    plt.close()

    return title


def plot_route_speed_and_map(route_data, speed_limit):
    w, h = matplotlib.figure.figaspect(9 / 16)
    _, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(1.25 * w, 1.25 * h), gridspec_kw={"width_ratios": [2, 1]}
    )
    wspace = 0.5 / 16
    padding_horizontal = 3 / 16 - wspace
    padding_vertical = 4 / 9
    plt.subplots_adjust(
        left=3 / 4 * padding_horizontal / 2,
        right=1 - 1 / 4 * padding_horizontal / 2,
        top=1 - padding_vertical / 2,
        bottom=padding_vertical / 2,
        wspace=wspace,
    )
    plot_route_speed(route_data, speed_limit, ax1)
    plot_route_map(route_data, speed_limit, ax2)


def plot_route_speed(route_data, speed_limit, ax):
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


def plot_route_map(route_data, speed_limit, ax):
    ax.set_axis_off()

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

    ax.set_aspect("equal", "datalim")
    ax.margins(0.15)
    cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik, zoom=17)
