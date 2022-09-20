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


def plot_statistics(max_speeds, hourly_counts, speed_limit):
    w, h = mpl.figure.figaspect(9 / 16)
    fig = plt.figure(figsize=(2.5 * w, 2.5 * h))
    gs = mpl.gridspec.GridSpec(2, 3, figure=fig)

    wspace = 2 / 16
    padding_horizontal = 4 / 16 - wspace
    padding_vertical = 1.5 / 9
    plt.subplots_adjust(
        left=padding_horizontal / 2,
        right=1 - padding_horizontal / 2,
        top=1 - padding_vertical / 2,
        bottom=padding_vertical / 2,
        wspace=wspace,
    )

    ax = fig.add_subplot(gs[0, 0])
    plot_max_speeds_histogram(max_speeds, speed_limit, ax)
    plot_max_speeds_box(max_speeds, speed_limit, fig.add_subplot(gs[1, 0], sharex=ax))

    ax = fig.add_subplot(gs[0, 1:3])
    plot_hourly_counts(hourly_counts, ax)
    plot_hourly_proportions(hourly_counts, fig.add_subplot(gs[1, 1:3], sharex=ax))


def plot_hourly_counts(hourly_counts, ax):
    no_speeding_color = "#33ff98"
    speeding_color = "#FF6961"

    @mpl.ticker.FuncFormatter
    def no_negative_values(x, pos):
        label = str(-x) if x < 0 else str(x)
        return label

    ax.yaxis.set_major_formatter(no_negative_values)

    ax.stackplot(
        hourly_counts.index,
        hourly_counts[True],
        colors=[speeding_color],
    )
    ax.stackplot(
        hourly_counts.index,
        -hourly_counts[False],
        colors=[no_speeding_color],
    )

    ax.plot([], [], speeding_color, label="Ylinopeus >= 4 km/h")
    ax.plot([], [], no_speeding_color, label="Ei ylinopeutta / lievä ylinopeus")
    ax.legend(loc="lower center", ncol=2)

    ylim = ax.get_ylim()
    ylim_max = np.abs(np.array(ylim)).max()
    ax.set_ylim(-ylim_max, ylim_max)

    ax.set_title("Nopeusrajoituksen noudattaminen tunneittain, bussien lukumäärä")


def plot_hourly_proportions(hourly_counts, ax):
    total = hourly_counts.sum(axis=1)
    plot_hourly_counts(hourly_counts.div(total, axis=0), ax)
    ax.set_title("Nopeusrajoituksen noudattaminen tunneittain, suhteellinen osuus")


def plot_max_speeds_box(max_speeds, speed_limit, ax):
    ax = sns.boxplot(
        data=max_speeds.reset_index()[["route_number", "max_speed"]],
        x="max_speed",
        y="route_number",
        flierprops={"marker": "x"},
    )

    for patch in ax.artists:
        fc = patch.get_facecolor()
        patch.set_facecolor(mpl.colors.to_rgba(fc, ALPHA))

    ylim = ax.get_ylim()
    ax.set_xlabel("Nopeus (km/h)")
    ax.set_ylabel("Linja")
    ax.vlines(speed_limit, *ylim, linestyle="dashed", color="black", alpha=ALPHA)
    ax.set_ylim(ylim)
    ax.set_title(f"Huippunopeudet linjoittain")


def plot_max_speeds_histogram(max_speeds, speed_limit, ax):
    max_speeds.max_speed.plot.hist(bins=20, alpha=ALPHA, ax=ax)
    ax.set_ylabel("Lukumäärä")
    ylim = ax.get_ylim()
    ax.vlines(speed_limit, *ylim, linestyle="dashed", color="black", alpha=ALPHA)
    ax.set_ylim(ylim)
    ax.set_title(f"Bussien huippunopeudet")
