import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from matplotlib import gridspec

from nopeusbotti.data import constants


def plot_statistics_to_file(df, speed_limit, path):
    max_speeds = get_max_speeds(df)
    hourly_counts = get_hourly_speeding_counts(max_speeds, speed_limit)
    plot_statistics(max_speeds, hourly_counts, speed_limit)

    title = "TODO TODO TODO"

    plt.suptitle(title)
    plt.savefig(path)
    plt.close()

    return title


def get_max_speeds(df):
    return (
        df.groupby(["route_number", "direction", "operating_day", "start_time"])
        .speed.agg(["max", "idxmax"])
        .rename(columns={"max": "max_speed", "idxmax": "max_speed_time"})
    )


def get_hourly_speeding_counts(max_speeds, speed_limit):
    return (
        (
            max_speeds.set_index("max_speed_time", drop=True) - speed_limit
            >= constants.SPEEDING_THRESHOLD
        )
        .rename(columns={"max_speed": "speeding"})
        .groupby("speeding")
        .resample("1H")
        .size()
        .unstack()
        .unstack()
        .unstack()
        .fillna(0)
    )


def plot_statistics(max_speeds, hourly_counts, speed_limit):
    w, h = matplotlib.figure.figaspect(9 / 16)
    fig = plt.figure(tight_layout=True, figsize=(2.5 * w, 2.5 * h))
    gs = gridspec.GridSpec(2, 2)
    plot_max_speeds_histogram(max_speeds, speed_limit, fig.add_subplot(gs[:, 0]))

    ax = fig.add_subplot(gs[0, 1])
    plot_hourly_counts(hourly_counts, ax)
    plot_hourly_proportions(hourly_counts, fig.add_subplot(gs[1, 1], sharex=ax))


def plot_hourly_counts(hourly_counts, ax):
    no_speeding_color = "#33ff98"
    speeding_color = "#FF6961"

    @ticker.FuncFormatter
    def no_negative_values(x, pos):
        label = str(-x) if x < 0 else str(x)
        return label

    ax.yaxis.set_major_formatter(no_negative_values)
    ax.stackplot(hourly_counts.index, hourly_counts[True], colors=[speeding_color])
    ax.stackplot(hourly_counts.index, -hourly_counts[False], colors=[no_speeding_color])
    ax.plot(
        [],
        [],
        speeding_color,
        label=f"Ylinopeus >= {constants.SPEEDING_THRESHOLD} km/h",
    )
    ax.plot([], [], no_speeding_color, label="Ei ylinopeutta / lievä ylinopeus")
    ax.legend(loc="lower center", ncol=2)

    ylim = ax.get_ylim()
    ylim_max = np.abs(np.array(ylim)).max()
    ax.set_ylim(-ylim_max, ylim_max)

    ax.set_title("Nopeusrajoituksen noudattaminen tunneittain")


def plot_hourly_proportions(hourly_counts, ax):
    total = hourly_counts.sum(axis=1)
    plot_hourly_counts(hourly_counts.div(total, axis=0), ax)
    ax.set_title("Nopeusrajoituksen noudattaminen tunneittain, suhteellinen osuus")


def plot_max_speeds_histogram(max_speeds, speed_limit, ax):
    max_speeds.max_speed.plot.hist(bins=20, alpha=0.7, ax=ax)
    ax.set_ylabel("Lukumäärä")
    ax.set_xlabel("Nopeus (km/h)")
    ylim = ax.get_ylim()
    ax.vlines(speed_limit, *ylim, linestyle="dashed", color="black")
    ax.set_ylim(ylim)
    ax.set_title(f"Bussien huippunopeudet {speed_limit} km/h rajoitusalueella")
