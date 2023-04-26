# STL
import enum
import uuid
from types import NoneType
from typing import Any, Set, Dict, List, Tuple, Optional
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

"""
everything is divided such that I can use `back_populates` because otherwise the interface is misery
it would require me to safety check the existence of users/guilds at every instance i might create one
so instead, let the db do that for me

it does mean i have two nearly identical tables that serve nearly identical purposes, which leads to some code duplication
some of that duplication is fixable; others are intentionaly different
"""


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


class Owner(enum.Enum):
    # not part of schema

    GUILD = "GUILD"
    USER = "USER"


class ConfigKey(enum.Enum):
    # user only
    REACTS = "reacts"
    OPENS = "opens"

    # guild only
    ROLE = "role"

    # both


class Guilds(Base):
    __tablename__ = "guilds"
    id = Column(BigInteger, primary_key=True, nullable=False)
    config = Column(NestedMutableJson, nullable=False, default={})

    default_icon_banner_id = Column(UUID, nullable=True)

    icons_banners = relationship("IconsBanners", back_populates="guild")
    guild_rules = relationship("GuildRules", back_populates="guild")


class Users(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, nullable=False)
    config = Column(NestedMutableJson, nullable=False, default={})

    user_rules = relationship("UserRules", back_populates="user")


class UserRules(Base):
    __tablename__ = "user_rules"
    id = Column(BigInteger, nullable=False)  # this is the container id
    owner_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    ctype = Column(Enum(Container), nullable=False)
    exception = Column(Boolean, nullable=False, default=False)

    user = relationship("Users", back_populates="user_rules")

    __table_args__ = (
        PrimaryKeyConstraint("id", "owner_id"),
        CheckConstraint(  # enums aren't in sqlite and we only perform this check on insert so sure
            ctype.in_([e.value for e in Container]),
            name="check_ctype_valid",
        ),
    )


class GuildRules(Base):
    # for OLD servers, the channel id for the default #general is the same as the server ID
    # ... this doesn't break anything, it's just weird that id li ken guild_id
    __tablename__ = "guild_rules"
    id = Column(BigInteger, nullable=False)
    owner_id = Column(BigInteger, ForeignKey("guilds.id"), nullable=False)
    ctype = Column(Enum(Container), nullable=False)
    exception = Column(Boolean, nullable=False, default=False)

    guild = relationship("Guilds", back_populates="guild_rules")

    __table_args__ = (
        PrimaryKeyConstraint("id", "owner_id"),
        CheckConstraint(
            ctype.in_([e.value for e in Container]),
            name="check_ctype_valid",
        ),
    )


class IconsBanners(Base):
    # conjoined due to pair relationship
    __tablename__ = "icons_banners"
    id = Column(UUID, primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"), nullable=False)
    author_id = Column(BigInteger, nullable=True)
    name = Column(String, nullable=False)
    last_used = Column(DateTime, nullable=False)
    config = Column(mutable_json_type(dbtype=JSON, nested=True), nullable=True)
    # TODO: phase, event, default
    icon = Column(LargeBinary, nullable=False)
    banner = Column(LargeBinary, nullable=True)

    guild = relationship("Guilds", back_populates="icons_banners")

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

    async def __insert_guild(self, guild_id: int, config: Optional[dict] = None):
        new_guild = Guilds(id=guild_id, config=config)
        self.s.add(new_guild)
        await self.s.commit()

    async def __insert_user(self, user_id: int):
        new_user = Users(id=user_id)
        self.s.add(new_user)
        await self.s.commit()

    async def __get_entity(  # necessary for sqlalchemy_json behavior
        self, owner_id: int, owner_type: Owner
    ) -> Users | Guilds:
        Table = owner_to_ent_table(owner_type)
        stmt = select(Table).where(Table.id == owner_id)
        result = await self.s.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity is None:
            entity = Table(id=owner_id, config={})  # TODO: do better?
            self.s.add(entity)
            await self.s.commit()
        return entity

    async def __get_config(self, owner_id: int, owner_type: Owner) -> Column:
        e = await self.__get_entity(owner_id, owner_type)
        return e.config

    async def __get_config_item(
        self,
        owner_id: int,
        owner_type: Owner,
        key: ConfigKey,
    ) -> Optional[JSONType]:
        config = await self.__get_config(owner_id, owner_type)
        return config.get(key.value) if config else None

    async def __set_config_item(
        self,
        owner_id: int,
        owner_type: Owner,
        key: ConfigKey,
        value: JSONType,
    ):
        entity = await self.__get_entity(owner_id, owner_type)
        entity.config[key.value] = value  # type: ignore
        # you can assign to Column with `sqlalchemy_json`
        await self.s.commit()

    async def set_reacts(self, owner_id: int, owner_type: Owner, reacts: List[str]):
        await self.__set_config_item(owner_id, owner_type, ConfigKey.REACTS, reacts)

    async def get_reacts(self, owner_id: int, owner_type: Owner):
        return await self.__get_config_item(owner_id, owner_type, ConfigKey.REACTS)

    async def upsert_rule(
        self,
        id: int,
        ctype: Container,
        owner_id: int,
        owner_type: Owner,
        exception: bool = False,
    ):
        Table = owner_to_rule_table(owner_type)
        stmt = (
            insert(Table)
            .values(
                id=id,
                owner_id=owner_id,
                ctype=ctype,
                exception=exception,
            )
            .on_conflict_do_update(  # type: ignore
                # pyright says .values can be None?
                index_elements=["id", "owner_id"],
                set_=dict(exception=exception),
            )
        )
        await self.s.execute(stmt)
        await self.s.commit()

    async def delete_rule(
        self,
        id: int,
        ctype: Container,
        owner_id: int,
        owner_type: Owner,
    ):
        Table = owner_to_rule_table(owner_type)
        stmt = delete(Table).where(
            (Table.id == id) & (Table.owner_id == owner_id) & (Table.ctype == ctype)
        )
        await self.s.execute(stmt)
        await self.s.commit()

    async def toggle_rule(
        self,
        id: int,
        ctype: Container,
        owner_id: int,
        owner_type: Owner,
        exception: bool = False,
    ):
        """
        Insert a rule if it is not in the database.
        Update a rule if it is in the database but different (exception field).
        Delete a rule if it is in the database.
        Return the action taken as a string.

        The name is a bit disingenuous since we can upsert, but my interface only has upsert so it's *fine*.
        """
        Table = owner_to_rule_table(owner_type)
        stmt = select(Table).where(
            (Table.id == id) & (Table.owner_id == owner_id) & (Table.ctype == ctype)
        )
        result = await self.s.execute(stmt)
        rule = result.scalar_one_or_none()

        if not rule:
            await self.upsert_rule(id, ctype, owner_id, owner_type, exception)
            return Action.INSERT

        if rule.exception != exception:
            await self.upsert_rule(id, ctype, owner_id, owner_type, exception)
            return Action.UPDATE

        await self.delete_rule(id, ctype, owner_id, owner_type)
        return Action.DELETE

    async def list_rules(
        self,
        owner_id: int,
        owner_type: Owner,
    ) -> Tuple[Dict[Container, Set[int]], Dict[Container, Set[int]]]:
        Table = owner_to_rule_table(owner_type)
        stmt = select(Table).where(Table.owner_id == owner_id)
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
                    IconsBanners.id != Guilds.default_icon_banner_id,
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
            update(Guilds)
            .where(Guilds.id == guild_id)
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


def owner_to_ent_table(owner_type: Owner) -> Guilds | Users:
    if owner_type == Owner.GUILD:
        return Guilds
    elif owner_type == Owner.USER:
        return Users

    raise ValueError("Invalid Owner %s", owner_type)


def owner_to_rule_table(owner_type: Owner) -> GuildRules | UserRules:
    if owner_type == Owner.GUILD:
        return GuildRules
    elif owner_type == Owner.USER:
        return UserRules

    raise ValueError("Invalid Owner %s", owner_type)
