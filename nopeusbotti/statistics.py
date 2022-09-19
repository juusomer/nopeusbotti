import logging
import uuid
from pathlib import Path
from typing import Optional

import pandas as pd

from nopeusbotti.api import twitter
from nopeusbotti.data import vehicle_positions
from nopeusbotti.plots import statistics

logger = logging.getLogger(__name__)


def generate_weekly_statistics(
    speed_limit: int,
    no_tweets: bool,
    plot_directory: Path,
    csv_directory: Path,
    end_time: Optional[pd.Timestamp] = None,
):

    if end_time is None:
        # Last week's Sunday
        end_time = pd.Timestamp() - pd.offsets.Week(weekday=6)

    start_time = end_time - pd.Timedelta(days=7)

    csv_files = [
        csv_directory / f"{date.year}-{date.month}-{date.day}.csv"
        for date in pd.date_range(start_time, end_time)
    ]

    print(csv_files)

    df = vehicle_positions.read_from_csv(*csv_files)
    plot_filename = plot_directory / (str(uuid.uuid4()) + ".png")
    title = statistics.plot_statistics_to_file(df, speed_limit, plot_filename)

    if no_tweets:
        return

    # twitter.send_tweet(title, plot_filename)
    # plot_filename.unlink()
