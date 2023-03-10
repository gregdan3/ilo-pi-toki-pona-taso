# STL
from math import floor
from typing import List, Tuple
from datetime import datetime, timedelta

# PDM
import numpy
from skyfield import api, almanac

TS = api.load.timescale()
EPH = api.load("de421.bsp")

# PHASE_LEN_DAYS = 30  # wikipedia
PHASE_LEN_DAYS = 30
# this makes our days too short; the real len is ~29.53 days
# but this stays in line with the emoji phase, so long as there are an equal number of emojis to use
# and our goal is to return the face emoji for the ~day following 0 and 180, the new and full moons
PHASE_LEN_DAYS_REAL = 29.53

# constants from skyfield
PHASE_LEN_DEG = 360.0
NEW_MOON_DEG = 0.0
FULL_MOON_DEG = 180.0

ONE_DAY_DEG = PHASE_LEN_DEG / PHASE_LEN_DAYS
NEW_MOON_END_DEG = NEW_MOON_DEG + ONE_DAY_DEG
FULL_MOON_END_DEG = FULL_MOON_DEG + ONE_DAY_DEG

#               0               90            180             270           360
PHASE_EMOJIS = "🌚🌑🌒🌒🌒🌒🌒🌓🌓🌔🌔🌔🌔🌔🌕🌝🌕🌖🌖🌖🌖🌖🌗🌗🌘🌘🌘🌘🌘🌑"
# yes it's hard to read so here's a traceable English version:
# face -> 1 new  -> 5 crescent -> 1 quarter -> 5 gibbous  -> 1 full ->
# face -> 1 full -> 5 gibbous  -> 1 quarter -> 5 crescent -> 1 new
EMOJIS_LEN = len(PHASE_EMOJIS)
EMOJI_STEP_SIZE = PHASE_LEN_DEG / EMOJIS_LEN

assert PHASE_LEN_DAYS == EMOJIS_LEN


def phase_at_datetime(t: datetime) -> almanac.Angle:
    dt = TS.from_datetime(t)
    return almanac.moon_phase(ephemeris=EPH, t=dt)


def datetime_to_degrees(t: datetime) -> numpy.float64:
    """Get the degree of the moon phase from a given datetime
    datetime MUST have timezone data"""
    deg = phase_at_datetime(t).degrees
    return deg  # pyright: ignore


def degrees_to_emoji(d: numpy.float64) -> str:
    """return an emoji representing the current moon phase
    the faced moon emojis are used during the ~24 hours once a full or new moon begins, respectively
    we don't benefit from `almanac.moon_phases()` here; it only tracks the quarters and majors
    """
    phase_index = floor(d // EMOJI_STEP_SIZE)
    emoji = PHASE_EMOJIS[phase_index]
    return emoji  # if some wacky bytes shit happens i will be mad


def datetime_to_emoji(t: datetime):
    d = datetime_to_degrees(t)
    emoji = degrees_to_emoji(d)
    return emoji


def degree_in_major_phase(d: numpy.float64) -> bool:
    """return True in the 24 hour period after a full moon or new moon begins given some time t"""
    return (  # pyright is wrong about comparing numpy.float64 and float
        NEW_MOON_DEG <= d < NEW_MOON_END_DEG  # pyright: ignore
        or FULL_MOON_DEG <= d < FULL_MOON_END_DEG  # pyright: ignore
    )


def date_in_major_phase(t: datetime) -> bool:
    d = datetime_to_degrees(t)
    return degree_in_major_phase(d)


def get_next_n_major_phases(
    start: datetime, n: int
) -> Tuple[List[datetime], List[datetime]]:
    """Return the start times of n new and full moons from the given start time forward
    Split into new and full moons as two lists for convenience; end user is responsible for interleaving
    """
    delta = timedelta(days=PHASE_LEN_DAYS_REAL) * (n / 2)
    # this is correct if PHASE_LEN_DAYS_REAL agrees with your ephemeris
    # will produce a date range containing n new/full moons
    end = start + delta

    start_ts = TS.from_datetime(start)
    end_ts = TS.from_datetime(end)
    time, phase = almanac.find_discrete(start_ts, end_ts, almanac.moon_phases(EPH))

    l = len(time)
    new_moons = [time[i] for i in range(l) if phase[i] == 0]
    full_moons = [time[i] for i in range(l) if phase[i] == 3]

    return new_moons, full_moons
