# STL
from datetime import datetime, timedelta

# PDM
import pytest

# LOCAL
from tenpo.phase_utils import (
    PHASES,
    major_phases_from,
    date_in_major_phase,
    major_phases_from_now,
)


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
    """demonstration, crosses a full moon"""
    date = datetime(year=2023, month=3, day=7, hour=0, minute=0).astimezone()
    delta = timedelta(minutes=5)
    full = False
    for i in range(600):
        in_phase = date_in_major_phase(date)
        if (in_phase and not full) or ((not in_phase) and full):
            full = not full
            term = "phase began at" if full else "phase ended at"
            print(term, date)

        if i < 81 or i >= 387:  # leading up to and ending phase
            assert not in_phase, i
        elif 81 <= i < 387:
            assert in_phase, i
        else:
            assert False, "Impossible moon_state?"
        date += delta


@pytest.mark.skip("unfinished test; same as previous")
def test_2023_march_07_09_clean():
    """demonstration, crosses a full moon"""
    start_date = datetime(year=2023, month=3, day=7, hour=0, minute=0).astimezone()
    end_date = start_date + timedelta(days=2)
    step_size = timedelta(minutes=5)

    full_moon_start = datetime(
        year=2023, month=3, day=7, hour=6, minute=45
    ).astimezone()
    full_moon_end = datetime(year=2023, month=3, day=8, hour=12, minute=50).astimezone()

    date = start_date
    while date <= end_date:
        in_phase = date_in_major_phase(date)

        if full_moon_start <= date < full_moon_end:
            assert in_phase, f"Expected in phase at {date}"
        else:
            assert not in_phase, f"Expected not in phase at {date}"

        date += step_size
