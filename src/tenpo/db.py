# STL
import enum
import uuid
from types import NoneType
from typing import Set, Dict, List, Tuple, Optional, cast
from datetime import datetime

# PDM
from asyncinit import asyncinit
from sqlalchemy import (
    JSON,
    Enum,
    Column,
    String,
    Boolean,
    DateTime,
    BigInteger,
    ForeignKey,
    LargeBinary,
    CheckConstraint,
    UniqueConstraint,
    PrimaryKeyConstraint,
    and_,
    delete,
    select,
    update,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy_json import NestedMutableJson, mutable_json_type
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.dialects.sqlite import Insert as insert
from sqlalchemy_utils.types.uuid import UUIDType as UUID

# LOCAL
from tenpo.log_utils import getLogger

LOG = getLogger()
Base = declarative_base()
JSONPrimitive = str | int | bool | NoneType
JSONType = JSONPrimitive | List[JSONPrimitive] | Dict[JSONPrimitive, JSONPrimitive]


class Action(enum.Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class Container(enum.Enum):
    # We HAVE to know what the type is when we read it from the DB
    # or else we're forced to ask discord which is which
    GUILD = "GUILD"
    CATEGORY = "CATEGORY"
    CHANNEL = "CHANNEL"


class ConfigKey(enum.Enum):
    # user only
    REACTS = "reacts"
    OPENS = "opens"

    # guild only
    ROLE = "role"
    ICON = "icon"

    # both


class Entity(Base):
    __tablename__ = "entity"  # guilds and users
    id = Column(BigInteger, primary_key=True, nullable=False)
    config = Column(NestedMutableJson, nullable=False, default={})

    rules = relationship("Rules", back_populates="entity")
    icons_banners = relationship("IconsBanners", back_populates="entity")


class Rules(Base):
    __tablename__ = "rules"
    id = Column(BigInteger, nullable=False)  # this is the container id
    eid = Column(BigInteger, ForeignKey("entity.id"), nullable=False)
    ctype = Column(Enum(Container), nullable=False)
    exception = Column(Boolean, nullable=False, default=False)

    entity = relationship("Entity", back_populates="rules")

    __table_args__ = (
        PrimaryKeyConstraint("id", "eid"),
        CheckConstraint(  # enums aren't in sqlite and we only perform this check on insert so sure
            ctype.in_([e.value for e in Container]),
            name="check_ctype_valid",
        ),
    )


class IconsBanners(Base):
    # conjoined due to pair relationship
    __tablename__ = "icons_banners"
    id = Column(UUID, primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    guild_id = Column(BigInteger, ForeignKey("entity.id"), nullable=False)
    author_id = Column(BigInteger, nullable=True)
    name = Column(String, nullable=False)
    last_used = Column(DateTime, nullable=False)
    config = Column(mutable_json_type(dbtype=JSON, nested=True), nullable=True)
    # TODO: phase, event, default
    icon = Column(LargeBinary, nullable=False)
    banner = Column(LargeBinary, nullable=True)

    entity = relationship("Entity", back_populates="icons_banners")

    __table_args__ = (
        UniqueConstraint("guild_id", "name", name="unique_guild_id_name"),
    )


@asyncinit
class TenpoDB:
    engine: AsyncEngine
    sgen: async_sessionmaker
    s: AsyncSession

    async def __init__(self, database_file: str):
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{database_file}")
        self.sgen = async_sessionmaker(bind=self.engine, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.s = self.sgen()

    async def close(self):
        await self.s.close()
        await self.engine.dispose()

    async def __get_entity(self, eid: int) -> Entity:
        stmt = select(Entity).where(Entity.id == eid)
        result = await self.s.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity is None:
            entity = Entity(id=eid, config={})  # TODO: do better?
            self.s.add(entity)
            await self.s.commit()
        return entity

    async def __get_config(self, eid: int) -> Column:
        e = await self.__get_entity(eid)
        return e.config

    async def __get_config_item(self, eid: int, key: ConfigKey) -> Optional[JSONType]:
        config = await self.__get_config(eid)
        return config.get(key.value) if config else None

    async def __set_config_item(
        self,
        eid: int,
        key: ConfigKey,
        value: JSONType,
    ):
        entity = await self.__get_entity(eid)
        entity.config[key.value] = value  # type: ignore
        # you can assign to Column with `sqlalchemy_json`
        await self.s.commit()

    async def set_reacts(self, eid: int, reacts: List[str]):
        await self.__set_config_item(eid, ConfigKey.REACTS, reacts)

    async def get_reacts(self, eid: int) -> List[str]:
        return cast(List[str], await self.__get_config_item(eid, ConfigKey.REACTS))

    async def get_opens(self, eid: int):
        opens = (
            cast(List[str], await self.__get_config_item(eid, ConfigKey.OPENS)) or []
        )
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

    async def upsert_rule(
        self, id: int, ctype: Container, eid: int, exception: bool = False
    ):
        stmt = (
            insert(Rules)
            .values(
                id=id,
                eid=eid,
                ctype=ctype,
                exception=exception,
            )
            .on_conflict_do_update(  # type: ignore
                # pyright says .values can be None?
                index_elements=["id", "eid"],
                set_=dict(exception=exception),
            )
        )
        await self.s.execute(stmt)
        await self.s.commit()

    async def delete_rule(self, id: int, ctype: Container, eid: int):
        stmt = delete(Rules).where(
            (Rules.id == id) & (Rules.eid == eid) & (Rules.ctype == ctype)
        )
        await self.s.execute(stmt)
        await self.s.commit()

    async def toggle_rule(
        self,
        id: int,
        ctype: Container,
        eid: int,
        exception: bool = False,
    ):
        """
        Insert a rule if it is not in the database.
        Update a rule if it is in the database but different (exception field).
        Delete a rule if it is in the database.
        Return the action taken as a string.

        The name is a bit disingenuous since we can upsert, but my interface only has upsert so it's *fine*.
        """
        stmt = select(Rules).where(
            (Rules.id == id) & (Rules.eid == eid) & (Rules.ctype == ctype)
        )
        result = await self.s.execute(stmt)
        rule = result.scalar_one_or_none()

        if not rule:
            await self.upsert_rule(id, ctype, eid, exception)
            return Action.INSERT

        if rule.exception != exception:
            await self.upsert_rule(id, ctype, eid, exception)
            return Action.UPDATE

        await self.delete_rule(id, ctype, eid)
        return Action.DELETE

    async def list_rules(
        self,
        eid: int,
    ) -> Tuple[Dict[Container, Set[int]], Dict[Container, Set[int]]]:
        stmt = select(Rules).where(Rules.eid == eid)
        result = await self.s.execute(stmt)
        found_rules = result.scalars().all()

        rules = {val: set() for val in Container}
        exceptions = {val: set() for val in Container}

        for rule in found_rules:
            assert isinstance(rule.id, int)
            exceptions[rule.ctype].add(rule.id) if rule.exception else rules[
                rule.ctype
            ].add(rule.id)

        return rules, exceptions

    async def insert_icon_banner(
        self,
        guild_id: int,
        author_id: Optional[int],
        name: str,
        last_used: datetime,
        config: dict,
        icon: bytes,
        banner: Optional[bytes] = None,
    ):
        if not last_used:
            last_used = datetime.now()
        stmt = (
            insert(IconsBanners)
            .values(
                guild_id=guild_id,
                author_id=author_id,
                name=name,
                last_used=last_used,
                config=config,
                icon=icon,
                banner=banner,
            )
            .on_conflict_do_nothing()
        )  # TODO: user reuses name la explode at them
        result = await self.s.execute(stmt)
        await self.s.commit()
        return result.inserted_primary_key[0]

    async def get_icon_banner_names(self, guild_id: int) -> List[str]:
        stmt = select(IconsBanners.name).where(IconsBanners.guild_id == guild_id)
        result = await self.s.execute(stmt)
        return [row.name for row in result.fetchall()]

    async def get_event_icon_banner(self, guild_id: int):
        """Returns the oldest non-default icon+banner pair"""
        stmt = (
            select(IconsBanners)
            .where(
                and_(
                    IconsBanners.guild_id == guild_id,
                    IconsBanners.id != Entity.default_icon_banner_id,
                )
            )
            .order_by(IconsBanners.last_used.asc())
            .limit(1)
        )
        result = await self.s.execute(stmt)
        icon_banner = result.scalar_one_or_none()
        return icon_banner

    async def get_icon_banner_by_name(
        self, guild_id: int, name: str
    ) -> Optional[IconsBanners]:
        stmt = (
            select(IconsBanners)
            .where(
                and_(
                    IconsBanners.guild_id == guild_id,
                    IconsBanners.name == name,
                )
            )
            .limit(1)
        )
        result = await self.s.execute(stmt)
        icon_banner = result.scalar_one_or_none()
        return icon_banner

    async def __set_default_icon_banner(
        self, guild_id: int, default_icon_banner_id: UUID
    ):
        stmt = (
            update(Entity)
            .where(Entity.id == guild_id)
            .values(default_icon_banner_id=default_icon_banner_id)
        )
        await self.s.execute(stmt)
        await self.s.commit()

    async def set_default_icon_banner(self, guild_id: int, name: str) -> None:
        stmt = (
            select(IconsBanners.id)
            .where(IconsBanners.guild_id == guild_id)
            .where(IconsBanners.name == name)
        )
        result = await self.s.execute(stmt)
        icon_banner_id = result.scalar_one_or_none()

        if not icon_banner_id:
            raise ValueError("No icon/banner found with the given name for the guild")

        await self.__set_default_icon_banner(guild_id, icon_banner_id)
