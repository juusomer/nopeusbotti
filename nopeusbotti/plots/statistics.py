import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from nopeusbotti.data import constants

ALPHA = 0.7


def plot_statistics_to_file(df, speed_limit, start_time, end_time, path):
    max_speeds = get_max_speeds(df, speed_limit)
    hourly_counts = get_hourly_speeding_counts(max_speeds)
    plot_statistics(max_speeds, hourly_counts, speed_limit)

    speeding_proportion = hourly_counts.sum()[True] / hourly_counts.sum().sum()
    max_speed = max_speeds.max_speed.max()
    most_moderate_route = max_speeds.groupby(level=0).speeding.mean().idxmin()
    date_format = "%d.%m.%Y"
    title = (
        f"Tilasot aikaväliltä {start_time.strftime(date_format)}–{end_time.strftime(date_format)}. "
        f"Ylinopeutta ajoi {speeding_proportion:.1%} busseista ja suurin nopeus oli {max_speed:.1f} km/h. "
        f"Keskimäärin maltillisimmin ajoivat linjan {most_moderate_route} bussit."
    )

    plt.suptitle(title)
    plt.savefig(path)
    plt.close()

    return title


def plot_hourly_counts(hourly_counts, ax):
    no_speeding_color = "#33ff98"
    speeding_color = "#FF6961"

    @mpl.ticker.FuncFormatter
    def no_negative_values(x, pos):
        label = str(-x) if x < 0 else str(x)
        return label

    ax.yaxis.set_major_formatter(no_negative_values)
    ax.stackplot(
        hourly_counts.index, hourly_counts[True], colors=[speeding_color], alpha=ALPHA
    )
    ax.stackplot(
        hourly_counts.index,
        -hourly_counts[False],
        colors=[no_speeding_color],
        alpha=ALPHA,
    )

    ax.plot([], [], speeding_color, label="Ylinopeus >= 4 km/h")
    ax.plot([], [], no_speeding_color, label="Ei ylinopeutta / lievä ylinopeus")
    ax.legend(loc="lower center", ncol=2)

    ylim = ax.get_ylim()
    ylim_max = np.abs(np.array(ylim)).max()
    ax.set_ylim(-ylim_max, ylim_max)
    ax.set_ylabel("Lukumäärä")

    ax.set_title("Nopeusrajoituksen noudattaminen aikavälillä")


def plot_max_speeds(max_speeds, speed_limit, ax, by):
    sns.boxplot(
        data=max_speeds.reset_index()[[by, "max_speed"]].sort_values(by),
        y="max_speed",
        x=by,
        flierprops={"marker": "x"},
        ax=ax,
    )

    for patch in ax.artists:
        fc = patch.get_facecolor()
        patch.set_facecolor(mpl.colors.to_rgba(fc, ALPHA))

    ax.set_ylabel("Nopeus (km/h)")
    xlim = ax.get_xlim()
    ax.hlines(speed_limit, *xlim, linestyle="dashed", alpha=ALPHA)
    ax.set_xlim(xlim)
    plt.xticks(rotation=45)


def plot_max_speeds_by_route(max_speeds, speed_limit, ax):
    plot_max_speeds(max_speeds, speed_limit, ax, "route_number")
    ax.set_xlabel("Linja")
    ax.set_title("Nopeudet linjoittain")


def plot_max_speeds_by_hour(max_speeds, speed_limit, ax):
    max_speeds = max_speeds.assign(hour=max_speeds.max_speed_time.dt.strftime("%H:00"))
    plot_max_speeds(max_speeds, speed_limit, ax, "hour")
    ax.set_title("Nopeudet eri kellonaikoina")
    ax.set_ylabel("Nopeus (km/h)")
    ax.set_xlabel("Kellonaika")


def plot_statistics(max_speeds, hourly_counts, speed_limit):
    w, h = mpl.figure.figaspect(9 / 16)
    fig = plt.figure(figsize=(2.5 * w, 2.5 * h))
    gs = mpl.gridspec.GridSpec(2, 3)

    ax = fig.add_subplot(gs[0, 0])
    plot_max_speeds_by_route(max_speeds, speed_limit, ax)
    plot_max_speeds_by_hour(
        max_speeds, speed_limit, fig.add_subplot(gs[0, 1:3], sharey=ax)
    )

    ax = fig.add_subplot(gs[1, 0:3])
    plot_hourly_counts(hourly_counts, ax)


def get_max_speeds(df, speed_limit):
    max_speeds = (
        df.groupby(["route_number", "direction", "operating_day", "start_time"])
        .speed.agg(["max", "idxmax"])
        .rename(columns={"max": "max_speed", "idxmax": "max_speed_time"})
    )
    return max_speeds.assign(
        speeding=max_speeds.max_speed >= speed_limit + constants.SPEEDING_THRESHOLD
    )


def get_hourly_speeding_counts(max_speeds):
    is_speeding = ~(
        max_speeds.pivot(
            columns="speeding", values="speeding", index="max_speed_time"
        ).isna()
    )
    return (
        is_speeding.astype(int)
        .reindex(columns=[True, False])
        .fillna(0)
        .resample("1H")
        .sum()
    )
