# STL
import typing
import logging
from math import floor
from typing import Tuple, Literal, Optional, Generator
from datetime import datetime, timedelta

# PDM
import numpy
from skyfield import api, almanac
from skyfield.timelib import Time

Phase = Literal["new", "full"]
PHASES = typing.get_args(Phase)

LOG = logging.getLogger("tenpo")
TS = api.load.timescale()
EPH = api.load("de421.bsp")

PHASE_LEN_DAYS = 30
# this makes our days too short; the real len is ~29.53 days
# but this stays in line with the emoji phase, so long as there are that many emojis
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
# new face  -> 1 new  -> 5 crescent -> 2 quarter -> 5 gibbous  -> 1 full ->
# full face -> 1 full -> 5 gibbous  -> 2 quarter -> 5 crescent -> 1 new
EMOJIS_LEN = len(PHASE_EMOJIS)
EMOJI_STEP_SIZE = PHASE_LEN_DEG / EMOJIS_LEN

assert PHASE_LEN_DAYS == EMOJIS_LEN


def now_skyfield():
    """skyfield demands a timezone'd datetime"""
    return datetime.now().astimezone()


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


def datetime_to_emoji(t: datetime) -> str:
    """get the emoji most closely representing the current phase during `t`"""
    d = datetime_to_degrees(t)
    emoji = degrees_to_emoji(d)
    return emoji


def degree_in_major_phase(d: numpy.float64) -> bool:
    """return True in the 24 hour period after a full moon or new moon begins given some `d` between 0 and 360
    following skyfield's contract, ~0-30 are new moons and ~180-210 are full moons"""
    return (  # pyright is wrong about comparing numpy.float64 and float
        NEW_MOON_DEG <= d < NEW_MOON_END_DEG  # pyright: ignore
        or FULL_MOON_DEG <= d < FULL_MOON_END_DEG  # pyright: ignore
    )


def date_in_major_phase(t: datetime) -> bool:
    """check if it's a full or new moon during the given datetime"""
    d = datetime_to_degrees(t)
    return degree_in_major_phase(d)


def is_major_phase() -> bool:
    """check if it's a full or new moon Right Now"""
    now = now_skyfield()
    return date_in_major_phase(now)


def major_phases_from(
    start: datetime, limit: Optional[int] = None
) -> Generator[Tuple[Time, Phase], None, None]:
    """return consecutive major phases starting from the given time, plus which phase it is as a string"""
    delta = timedelta(days=PHASE_LEN_DAYS_REAL) / 2

    end = start  # this is to get cleaner while loop behavior
    start -= delta  # but also bruh
    count = 0

    while True:
        start = end
        end += delta

        start_ts = TS.from_datetime(start)
        end_ts = TS.from_datetime(end)

        times, phases = almanac.find_discrete(
            start_ts, end_ts, almanac.moon_phases(EPH)
        )
        for time, phase in zip(times, phases):
            # will always contain exactly 1 new major phase
            # but if somehow it doesn't, it'll only find 0/2 phases and continue without incrementing count
            if phase not in (0, 2):
                continue
            yield time, PHASES[phase // 2]  # news are 0, fulls are 2, lol
            count += 1
        if limit and count >= limit:
            return


def major_phases_from_now(
    limit: Optional[int] = None,
) -> Generator[Tuple[Time, Phase], None, None]:
    now = now_skyfield()
    yield from major_phases_from(now, limit)
