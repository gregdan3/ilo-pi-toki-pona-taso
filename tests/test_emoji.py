# STL
from datetime import datetime, timedelta

# PDM
from skyfield import almanac

# LOCAL
from tenpo.phase_utils import (
    datetime_to_emoji,
    phase_at_datetime,
    date_in_major_phase,
    datetime_to_degrees,
)


def test_daily():
    date = datetime(year=2023, month=3, day=1, hour=0, minute=0).astimezone()
    delta = timedelta(hours=8)

    for _ in range(45 * 3):  # 90 days test
        emoji = datetime_to_emoji(date)
        degree = datetime_to_degrees(date)
        phase_state = date_in_major_phase(date)
        if emoji == "🌝" or emoji == "🌚":
            assert phase_state, "Faced phase %s at wrong time!" % emoji
        else:
            assert not phase_state, "Normal phase %s at wrong time!" % emoji
        if emoji == "🌓" or emoji == "🌗":
            assert (  # fairly liberal but we don't need crazy precision
                75 <= degree <= 110 or 255 <= degree <= 300
            ), "emoji %s appeared at %s" % (emoji, degree)

        print(date, emoji, phase_state)
        date += delta
