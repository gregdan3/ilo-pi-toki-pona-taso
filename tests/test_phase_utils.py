# STL
from datetime import datetime, timezone, timedelta

# PDM
import pytest

# LOCAL
from tenpo.phase_utils import (
    PHASES,
    datetime_to_emoji,
    major_phases_from,
    date_in_major_phase,
    datetime_to_degrees,
    major_phases_from_now,
)

MY_TZ = timezone(timedelta(hours=-5))

DATETIMES_KNOWN_PHASE = (
    (
        datetime(year=2023, month=8, day=1, hour=13, minute=32).astimezone(MY_TZ),
        True,
        "Start of August 2023 full moon (to minute)",
    ),
    (
        datetime(year=2023, month=8, day=1, hour=23, minute=0).astimezone(MY_TZ),
        True,
        "Middle of August 2023 full moon",
    ),
    (
        datetime(year=2023, month=8, day=2, hour=13, minute=30).astimezone(MY_TZ),
        True,
        "End of August 2023 full moon (to minute)",
    ),
    (
        datetime(year=2023, month=8, day=1, hour=13, minute=28).astimezone(MY_TZ),
        False,
        "Before beginning of August 2023 full moon",
    ),
    (
        datetime(year=2023, month=8, day=2, hour=13, minute=32).astimezone(MY_TZ),
        False,
        "After end of August 2023 full moon",
    ),
)


@pytest.mark.parametrize(
    "tz_datetime, in_major_phase, annotation", DATETIMES_KNOWN_PHASE
)
def test_expected_times(tz_datetime, in_major_phase, annotation):
    if not annotation:
        annotation = "No annotation"
    assert date_in_major_phase(tz_datetime) == in_major_phase, annotation


def test_generate_phases_consecutively():
    date = datetime(year=2010, month=3, day=1).astimezone()
    count = 0
    limit = 25
    for time, phase in major_phases_from(date, limit=limit):
        assert time.tt
        assert phase in PHASES
        count += 1
    assert count == limit


def test_generate_phases_consecutively_from_now():
    count = 0
    limit = 25
    for time, phase in major_phases_from_now(limit=limit):
        assert time.tt  # you can't directly assert time bc of its broken __len__
        assert phase in PHASES
        count += 1
    assert count == limit


def test_2023_march_07_09():
    """ """
    date = datetime(year=2023, month=3, day=7, hour=0, minute=0).astimezone(MY_TZ)
    fm_start = datetime(year=2023, month=3, day=7, hour=6, minute=41).astimezone(MY_TZ)
    # 1 min after
    fm_end = datetime(year=2023, month=3, day=8, hour=6, minute=39).astimezone(MY_TZ)
    # 1 min before
    delta = timedelta(minutes=20)
    full = False
    for _ in range(600):
        full = fm_start <= date <= fm_end
        assert full == date_in_major_phase(date), f"Desynced phase at {date}"
        date += delta


@pytest.mark.skip("Horribly conceived test")
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

        date += delta
