# TODO: REFACTOR: Divide DB interface based on purpose i.e. entity evaluation, image handling, calendar handling, etc

# STL
import enum
from typing import Any, Set, Dict, List, Tuple, Literal, Optional, TypeAlias, cast
from contextlib import asynccontextmanager

# PDM
from sqlalchemy import (
    Enum,
    Column,
    Boolean,
    BigInteger,
    ForeignKey,
    CheckConstraint,
    PrimaryKeyConstraint,
    delete,
    select,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy_json import NestedMutableJson
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.dialects.sqlite import Insert as insert

# LOCAL
from tenpo.log_utils import getLogger
from tenpo.phase_utils import is_major_phase
from tenpo.croniter_utils import EventTimer, parse_delta

LOG = getLogger()
Base = declarative_base()
JSONType: TypeAlias = (
    dict[str, "JSONType"] | list["JSONType"] | str | int | float | bool | None
)

DEFAULT_REACTS = [
    "🌵",
    "🌲",
    "🌲",
    "🌲",
    "🌲",
    "🌲",
    "🌳",
    "🌳",
    "🌳",
    "🌳",
    "🌳",
    "🌴",
    "🌴",
    "🌴",
    "🌴",
    "🌴",
    "🌱",
    "🌱",
    "🌱",
    "🌱",
    "🌱",
    "🌿",
    "🌿",
    "🌿",
    "🌿",
    "🌿",
    "🍀",
    "🍃",
    "🍂",
    "🍁",
    "🌷",
    "🌺",
    "🌻",
    "🐝",
    "🐌",
    "🐛",
    "🐞",
    "🦋",
]
DEFAULT_RESPONSE = "sitelen"
DEFAULT_TIMER = "ala"
DEFAULT_TIMEZONE = "UTC"


class Pali(enum.Enum):
    PANA = 0
    ANTE = 1
    WEKA = 2


class IjoSiko(enum.Enum):
    # We HAVE to know what the type is when we read it from the DB
    # or else we're forced to ask discord which is which
    GUILD = "GUILD"
    CATEGORY = "CATEGORY"
    CHANNEL = "CHANNEL"
    USER = "USER"


class ConfigKey(enum.Enum):
    # user only
    REACTS = "reacts"
    OPENS = "opens"
    RESPONSE = "response"

    # guild only
    ROLE = "role"
    CALENDAR = "calendar"  # moon calendar channel
    CRON = "cron"  # cron string
    LENGTH = "length"  # timedelta
    TIMING = "timer"  # timing method (cron, ale, ala)
    TIMEZONE = "timezone"

    # both
    DISABLED = "disabled"


class ConfigKeyTypes(enum.Enum):
    REACTS = List[str]
    OPENS = List[str]
    RESPONSE = Literal["sitelen", "weka"]

    ROLE = int  # role id
    CALENDAR = int  # channel id
    CRON = str
    LENGTH = str  # TODO
    TIMEZONE = str
    TIMER = str

    DISABLED = bool


class NasinTenpo(enum.Enum):
    ALE = "ale"
    ALA = "ala"
    MUN = "mun"
    WILE = "wile"


Lawa = Dict[IjoSiko, Set[int]]
IjoPiLawaKen = [IjoSiko.GUILD, IjoSiko.CATEGORY, IjoSiko.CHANNEL]


class Entity(Base):
    __tablename__ = "entity"  # guilds and users
    id = Column(BigInteger, primary_key=True, nullable=False)
    config = Column(NestedMutableJson, nullable=False, default={})

    rules = relationship("Rules", back_populates=__tablename__)


class Rules(Base):
    __tablename__ = "rules"
    id = Column(BigInteger, nullable=False)  # this is the container id
    eid = Column(BigInteger, ForeignKey("entity.id"), nullable=False)
    ctype = Column(Enum(IjoSiko), nullable=False)
    exception = Column(Boolean, nullable=False, default=False)

    entity = relationship("Entity", back_populates=__tablename__)

    __table_args__ = (
        PrimaryKeyConstraint("id", "eid"),
        CheckConstraint(ctype.in_(IjoPiLawaKen), name="check_ctype_valid"),
    )


class TenpoDB:
    engine: AsyncEngine
    sgen: async_sessionmaker

    """
    Any function which
    - exposes a session parameter
    - exposes a config key parameter
    Must be protected (`__methodname`).
    """

    def __init__(self, database_file: str):
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{database_file}")
        self.sgen = async_sessionmaker(bind=self.engine, expire_on_commit=False)

    async def __ainit__(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self):
        await self.engine.dispose()

    @asynccontextmanager
    async def session(self):
        async with self.sgen() as s:
            yield s

    async def __get_entity(self, s: AsyncSession, eid: int) -> Entity:
        stmt = select(Entity).where(Entity.id == eid)
        result = await s.execute(stmt)

        if (entity := result.scalar_one_or_none()) is None:
            entity = Entity(id=eid, config={})
            s.add(entity)
            await s.commit()
        return entity

    async def __get_config(self, eid: int) -> Column:
        async with self.session() as s:
            e = await self.__get_entity(s, eid)
            return e.config

    async def __set_config(self, eid: int, value: JSONType):
        async with self.session() as s:
            e = await self.__get_entity(s, eid)
            e.config = value
            await s.commit()

    async def __get_config_item(
        self, eid: int, key: ConfigKey, default: Any = None
    ) -> Optional[JSONType]:
        config = await self.__get_config(eid)
        item = config.get(key.value, default) if config else default
        return item if (item is not None and item) else default

    async def __set_config_item(
        self,
        eid: int,
        key: ConfigKey,
        value: JSONType,
    ):
        async with self.session() as s:
            entity = await self.__get_entity(s, eid)
            entity.config[key.value] = value  # type: ignore
            # you can assign to Column with `sqlalchemy_json`
            await s.commit()

    async def reset_config(self, eid: int):
        await self.__set_config(eid, {})

    async def reset_rules(self, eid: int):
        rules, exceptions = await self.list_rules(eid)
        for ctype, ids in rules.items():
            for id in ids:
                resp = await self.upsert_rule(id, ctype, eid, False)
                assert resp == Pali.WEKA, (id, ctype, eid, False, resp)
        for ctype, ids in exceptions.items():
            for id in ids:
                resp = await self.upsert_rule(id, ctype, eid, True)
                assert resp == Pali.WEKA, (id, ctype, eid, True, resp)

    async def set_reacts(self, eid: int, reacts: List[str]):
        await self.__set_config_item(eid, ConfigKey.REACTS, reacts)

    async def get_reacts(self, eid: int) -> List[str]:
        return cast(
            List[str],
            await self.__get_config_item(eid, ConfigKey.REACTS, DEFAULT_REACTS),
        )

    async def set_disabled(self, eid: int, disabled: bool):
        await self.__set_config_item(eid, ConfigKey.DISABLED, disabled)

    async def get_disabled(self, eid: int) -> bool:
        return cast(bool, await self.__get_config_item(eid, ConfigKey.DISABLED, False))

    async def toggle_disabled(self, eid: int) -> bool:
        to_set = not await self.get_disabled(eid)
        await self.set_disabled(eid, to_set)
        return to_set

    async def get_opens(self, eid: int) -> List[str]:
        opens = cast(List[str], await self.__get_config_item(eid, ConfigKey.OPENS, []))
        return opens

    async def toggle_open(self, eid: int, open: str) -> bool:
        # TODO: is it better to extend the list in sqlalchemy_json?
        opens = await self.get_opens(eid)
        if is_in := open in opens:
            opens.remove(open)
        else:
            opens.append(open)
        await self.__set_config_item(eid, ConfigKey.OPENS, opens)
        return not is_in

    async def get_role(self, eid: int) -> Optional[int]:
        return await self.__get_config_item(eid, ConfigKey.ROLE)

    async def set_role(self, eid: int, role: Optional[int]):
        return await self.__set_config_item(eid, ConfigKey.ROLE, role)

    async def toggle_role(self, eid: int, role: int) -> bool:
        config_role = await self.get_role(eid)
        is_same = role == config_role
        to_assign = None if is_same else role
        await self.set_role(eid, to_assign)
        return not is_same  # true = wrote, false = deleted

    async def get_cron(self, eid: int) -> str:
        return cast(str, await self.__get_config_item(eid, ConfigKey.CRON))

    async def set_cron(self, eid: int, cron: str):
        return await self.__set_config_item(eid, ConfigKey.CRON, cron)

    async def get_timezone(self, eid: int) -> str:
        return cast(
            str, await self.__get_config_item(eid, ConfigKey.TIMEZONE, DEFAULT_TIMEZONE)
        )

    async def set_timezone(self, eid: int, timezone: str):
        return await self.__set_config_item(eid, ConfigKey.TIMEZONE, timezone)

    async def get_length(self, eid: int) -> str:
        return cast(str, await self.__get_config_item(eid, ConfigKey.LENGTH))

    async def set_length(self, eid: int, length: str):
        return await self.__set_config_item(eid, ConfigKey.LENGTH, length)

    async def get_timing(self, eid: int) -> str:  # DEFAULT: never
        return await self.__get_config_item(eid, ConfigKey.TIMING, DEFAULT_TIMER)

    async def set_timing(self, eid: int, timer: str):
        return await self.__set_config_item(eid, ConfigKey.TIMING, timer)

    async def get_event_timer(self, eid: int) -> EventTimer:
        c = await self.get_cron(eid)
        t = await self.get_timezone(eid)
        d = await self.get_length(eid)
        return EventTimer(c, t, d)

    async def get_response(self, eid: int) -> str:  # DEFAULT: react
        return await self.__get_config_item(eid, ConfigKey.RESPONSE, DEFAULT_RESPONSE)

    async def set_response(self, eid: int, response: str):
        return await self.__set_config_item(eid, ConfigKey.RESPONSE, response)

    async def get_calendar(self, eid: int) -> Optional[int]:
        return await self.__get_config_item(eid, ConfigKey.CALENDAR)

    async def set_calendar(self, eid: int, calendar: Optional[int]):
        return await self.__set_config_item(eid, ConfigKey.CALENDAR, calendar)

    async def get_calendars(self) -> List[int]:
        async with self.session() as s:
            stmt = select(Entity.id, Entity.config[ConfigKey.CALENDAR.value]).where(
                Entity.config[ConfigKey.CALENDAR.value].isnot(None)
            )
            result = await s.execute(stmt)
            entities_with_calendar = result.all()
        calendars = [calendar for _, calendar in entities_with_calendar if calendar]
        # TODO: fix stmt to actually filter at DB side
        return calendars

    async def toggle_calendar(self, eid: int, calendar: int) -> bool:
        config_calendar = await self.get_calendar(eid)
        is_same = calendar == config_calendar
        to_assign = None if is_same else calendar
        await self.set_calendar(eid, to_assign)
        return not is_same  # true = wrote, false = deleted

    async def __upsert_rule(
        self,
        s: AsyncSession,
        id: int,
        ctype: IjoSiko,
        eid: int,
        exception: bool = False,
    ):
        stmt = (
            insert(Rules)
            .values(
                id=id,
                eid=eid,
                ctype=ctype,
                exception=exception,
            )
            .on_conflict_do_update(
                index_elements=["id", "eid"],
                set_=dict(exception=exception),
            )
        )
        await s.execute(stmt)
        await s.commit()

    async def __delete_rule(self, s: AsyncSession, id: int, ctype: IjoSiko, eid: int):
        stmt = delete(Rules).where(
            (Rules.id == id) & (Rules.eid == eid) & (Rules.ctype == ctype)
        )
        await s.execute(stmt)
        await s.commit()

    async def upsert_rule(
        self,
        id: int,
        ctype: IjoSiko,
        eid: int,
        exception: bool = False,
    ):
        """
        Insert a rule if it is not in the database.
        Update a rule if it is in the database but different (exception field).
        Delete a rule if it is in the database.
        Return the action taken as a string.
        """
        async with self.session() as s:
            stmt = select(Rules).where(
                (Rules.id == id) & (Rules.eid == eid) & (Rules.ctype == ctype)
            )
            result = await s.execute(stmt)
            rule = result.scalar_one_or_none()

            if not rule:
                await self.__upsert_rule(s, id, ctype, eid, exception)
                return Pali.PANA

            if rule.exception != exception:
                await self.__upsert_rule(s, id, ctype, eid, exception)
                return Pali.ANTE

            await self.__delete_rule(s, id, ctype, eid)
            return Pali.WEKA

    async def list_rules(self, eid: int) -> Tuple[Lawa, Lawa]:
        async with self.session() as s:
            stmt = select(Rules).where(Rules.eid == eid)
            result = await s.execute(stmt)
            found_rules = result.scalars().all()

            rules = {val: set() for val in IjoPiLawaKen}
            exceptions = {val: set() for val in IjoPiLawaKen}

            for rule in found_rules:
                assert isinstance(rule.id, int)
                (
                    exceptions[rule.ctype].add(rule.id)
                    if rule.exception
                    else rules[rule.ctype].add(rule.id)
                )

            return rules, exceptions

    async def in_checked_channel(
        self, eid: int, channel_id: int, category_id: Optional[int], guild_id: int
    ) -> bool:
        rules, exceptions = await self.list_rules(eid)

        if channel_id in rules[IjoSiko.CHANNEL]:
            return True
        if channel_id in exceptions[IjoSiko.CHANNEL]:
            return False

        if category_id in rules[IjoSiko.CATEGORY]:
            return True
        if category_id in exceptions[IjoSiko.CATEGORY]:
            return False

        if guild_id in rules[IjoSiko.GUILD]:
            return True
        # guilds cannot have exceptions
        # if guild_id in exceptions[Container.GUILD]:
        #     return False

        return False

    async def is_event_time(self, eid: int) -> bool:
        timing_method = await self.get_timing(eid)
        if timing_method == "ale":
            return True
        elif timing_method == "ala":
            return False
        elif timing_method == "mun":
            return is_major_phase()
        elif timing_method == "wile":
            timer = await self.get_event_timer(eid)
            return timer.now_in_range()
        return False

    async def startswith_ignorable(self, eid: int, message: str) -> bool:
        opens = await self.get_opens(eid)
        for ignorable in opens:
            if message.startswith(ignorable):
                return True
        return False


async def TenpoDBFactory(database_file: str) -> TenpoDB:
    t = TenpoDB(database_file=database_file)
    await t.__ainit__()
    return t
