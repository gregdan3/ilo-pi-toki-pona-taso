# STL
from typing import Tuple, Union, Generator
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
        super().__init__("open tenpo li pakala: `%s`" % cron)


class InvalidTZ(InvalidEventTimer):
    def __init__(self, timezone: str) -> None:
        super().__init__("nasin tenpo li pakala: `%s`" % timezone)


class InvalidDelta(InvalidEventTimer):
    def __init__(self, delta: str) -> None:
        super().__init__("suli tenpo li pakala: `%s`" % delta)


class EventTimer:
    __tz: ValidTZ
    __cron: croniter
    __delta: timedelta

    def __init__(self, cron_str: str, tz_str: str, delta_str: str):
        if not tz_str:
            raise InvalidTZ(tz_str)
        if not cron_str:
            raise InvalidCron(cron_str)
        if not delta_str:
            raise InvalidDelta(delta_str)

        tz = gettz(tz_str)
        if not isinstance(tz, ValidTZ):
            raise InvalidTZ(tz_str)
        self.__tz = tz

        if not croniter.is_valid(cron_str):
            raise InvalidCron(cron_str)
        self.__cron = croniter(cron_str, datetime.now(tz))

        delta = timeparse(delta_str, granularity="minutes")
        if not isinstance(delta, int):
            raise InvalidDelta(delta_str)
        self.__delta = timedelta(seconds=delta)

    def __normalize_to_now(self) -> datetime:
        """
        Set current croniter to use `datetime.now` with the configured timezone.
        Return the created datetime.
        """
        now = datetime.now(tz=self.__tz)
        self.__cron.set_current(start_time=now)
        return now

    def now_in_range(self):
        now = self.__normalize_to_now()
        last = self.__cron.get_prev(datetime)
        # LOG.debug("%s %s %s", now, last, last + self.__delta)

        return last <= now < (last + self.__delta)

    def get_starts(self, n: int = 3) -> Generator[datetime, None, None]:
        self.__normalize_to_now()
        for _ in range(n):
            yield self.__cron.get_next(datetime)

    def get_ranges(
        self, n: int = 3
    ) -> Generator[Tuple[datetime, datetime], None, None]:
        self.__normalize_to_now()
        for _ in range(n):
            nxt = self.__cron.get_next(datetime)
            yield (nxt, nxt + self.__delta)
