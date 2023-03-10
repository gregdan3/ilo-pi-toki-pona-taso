# STL
from datetime import datetime, timedelta

# PDM
import pytest

# LOCAL
from tenpo.phase_utils import date_in_major_phase, get_next_n_major_phases


def test_2023_march_07_09():
    """demonstration, crosses a full moon"""
    date = datetime(year=2023, month=3, day=7, hour=0, minute=0).astimezone()
    # TODO: will this fail if i change timezones? it might lol
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


def test_get_major_phases():
    date = datetime(year=1900, month=3, day=7, hour=0, minute=0).astimezone()
    delta = timedelta(days=1000)
    to_fetch = 10
    for _ in range(5):
        # very lazy demonstration that the function holds no matter the range
        news, fulls = get_next_n_major_phases(date, to_fetch)
        assert len(news) + len(fulls) == to_fetch
        to_fetch *= 2
        delta *= 2
        date += delta
