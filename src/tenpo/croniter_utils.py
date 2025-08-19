# STL
from typing import Tuple, Union, Generator, cast
from datetime import datetime, timedelta

# PDM
from croniter import croniter
from dateutil.tz import gettz, tzstr, tzfile, tzlocal
from pytimeparse import parse as timeparse

# LOCAL
from tenpo.log_utils import getLogger

ValidTZ = tzlocal | tzfile | tzstr

LOG = getLogger()


class InvalidEventTimer(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class InvalidCron(InvalidEventTimer):
    def __init__(self, cron: str) -> None:
        super().__init__("sona tenpo li pakala: `%s`" % cron)


class InvalidTZ(InvalidEventTimer):
    def __init__(self, timezone: str) -> None:
        super().__init__("nasin tenpo li pakala: `%s`" % timezone)


class InvalidDelta(InvalidEventTimer):
    def __init__(self, delta: str) -> None:
        super().__init__("suli tenpo li pakala: `%s`" % delta)


def parse_delta(delta_str: str) -> timedelta:
    if not delta_str:
        raise InvalidDelta(delta_str)
    delta = timeparse(delta_str, granularity="minutes")
    if not isinstance(delta, int) or not delta > 0:
        raise InvalidDelta(delta_str)
    delta = timedelta(seconds=delta)
    return delta


def parse_timezone(tz_str: str) -> ValidTZ:
    if not tz_str:
        raise InvalidTZ(tz_str)
    tz = gettz(tz_str)
    if not isinstance(tz, ValidTZ):
        raise InvalidTZ(tz_str)
    return tz


def parse_cron(cron_str: str, tz: ValidTZ) -> croniter:
    if not cron_str:
        raise InvalidCron(cron_str)
    if not croniter.is_valid(cron_str):
        raise InvalidCron(cron_str)
    return croniter(cron_str, datetime.now(tz))


class EventTimer:
    __tz: ValidTZ
    __cron: croniter
    __delta: timedelta

    def __init__(self, cron_str: str, tz_str: str, delta_str: str):
        self.__tz = parse_timezone(tz_str)
        self.__cron = parse_cron(cron_str, self.__tz)
        self.__delta = parse_delta(delta_str)

    def __normalize_to_now(self) -> datetime:
        """
        Set current croniter to use `datetime.now` with the configured timezone.
        Return the created datetime.
        """
        now = datetime.now(tz=self.__tz)
        self.__cron.set_current(start_time=now)
        return now

    def get_prev(self, ref: datetime | None = None) -> datetime:
        if not ref:
            ref = self.__normalize_to_now()
        return self.__cron.get_prev(datetime, ref)

    def get_next(self, ref: datetime | None = None) -> datetime:
        if not ref:
            ref = self.__normalize_to_now()
        # it incorrectly claims to return a float...
        return cast(datetime, cast(object, self.__cron.get_next(datetime, ref)))

    def get_prev_range(self, ref: datetime | None = None) -> tuple[datetime, datetime]:
        start = self.get_prev(ref)
        return start, start + self.__delta

    def get_next_range(self, ref: datetime | None = None) -> tuple[datetime, datetime]:
        start = self.get_next(ref)
        return start, start + self.__delta

    def get_events_from(
        self,
        n: int = 3,
        ref: datetime | None = None,
    ) -> Generator[Tuple[datetime, datetime], None, None]:
        if not ref:
            ref = self.__normalize_to_now()
        for _ in range(n):
            start, end = self.get_next_range(ref)
            yield start, end
            # Advance reference slightly past the end of the current event
            ref = end + self.__delta

    def is_event_on(self, ref: datetime | None = None) -> bool:
        if not ref:
            ref = self.__normalize_to_now()
        start, end = self.get_prev_range(ref)
        return start <= ref < end
