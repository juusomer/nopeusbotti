import logging
import uuid
from pathlib import Path
from typing import Optional

import pandas as pd

from nopeusbotti.api import twitter
from nopeusbotti.data import vehicle_positions
from nopeusbotti.plots import statistics

logger = logging.getLogger(__name__)


def generate_statistics(
    speed_limit: int,
    no_tweets: bool,
    plot_directory: Path,
    csv_directory: Path,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
):

    if start_date is None:
        # Last week's Monday
        start_date = pd.Timestamp.now() - 2 * pd.offsets.Week(weekday=0)

    if end_date is None:
        # Week from start date
        end_date = start_date + pd.Timedelta(days=6)

    logger.info(
        f"Producing statistics between {start_date.date()} and {end_date.date()}"
    )

    csv_files = [
        csv_directory / f"{date.year}-{date.month:02}-{date.day:02}.csv"
        for date in pd.date_range(start_date, end_date)
    ]

    logger.info(f"Reading CSV data from {csv_files}")
    df = vehicle_positions.read_from_csv(*csv_files)

    plot_filename = plot_directory / (str(uuid.uuid4()) + ".png")

    logger.info(f"Plotting statistics to {plot_filename}")
    plot_directory.mkdir(parents=True, exist_ok=True)
    title = statistics.plot_statistics_to_file(
        df, speed_limit, start_date, end_date, plot_filename
    )

    if no_tweets:
        return

    logger.info(f"Sending {plot_filename} to Twitter")
    twitter.send_tweet(
        f"{title} Aiempia tilastoja voi selata tunnisteella {get_statistics_hashtag()}.",
        plot_filename,
    )

    plot_filename.unlink()


def get_statistics_hashtag():
    return f"#tilastot_{twitter.get_username()}"
