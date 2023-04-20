# STL
import enum
import uuid
import logging
from typing import Set, Dict, List, Tuple, Union, Optional, cast
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
    and_,
    select,
    update,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy_json import mutable_json_type
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.dialects.sqlite import Insert as insert
from sqlalchemy_utils.types.uuid import UUIDType as UUID

LOG = logging.getLogger("tenpo")
Base = declarative_base()

"""
everything is divided such that I can use `back_populates` because otherwise the interface is misery
it would require me to safety check the existence of users/guilds at every instance i might create one
so instead, let the db do that for me

it does mean i have two nearly identical tables that serve nearly identical purposes, which leads to some code duplication
some of that duplication is fixable; others are intentionaly different
"""


class Container(enum.Enum):
    GUILD = "GUILD"
    CATEGORY = "CATEGORY"
    CHANNEL = "CHANNEL"


class Owner(enum.Enum):
    # not part of schema

    GUILD = "GUILD"
    USER = "USER"


class Guilds(Base):
    __tablename__ = "guilds"
    id = Column(BigInteger, primary_key=True, nullable=False)
    config = Column(mutable_json_type(dbtype=JSON, nested=True), nullable=True)

    default_icon_banner_id = Column(UUID, nullable=True)

    icons_banners = relationship("IconsBanners", back_populates="guild")
    guild_rules = relationship("GuildRules", back_populates="guild")


class Users(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, nullable=False)
    config = Column(mutable_json_type(dbtype=JSON, nested=True), nullable=True)

    user_rules = relationship("UserRules", back_populates="user")


class UserRules(Base):
    __tablename__ = "user_rules"
    id = Column(BigInteger, primary_key=True)  # this is the container id
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    ctype = Column(Enum(Container), nullable=False)
    exception = Column(Boolean, nullable=False)

    user = relationship("Users", back_populates="user_rules")

    __table_args__ = (  # enums aren't in sqlite and we only perform this check on insert so sure
        CheckConstraint(
            ctype.in_([e.value for e in Container]),
            name="check_ctype_valid",
        ),
    )


class GuildRules(Base):
    # for OLD servers, the channel id for the default #general is the same as the server ID
    # ... this doesn't break anything, it's just weird that id li ken guild_id
    __tablename__ = "guild_rules"
    id = Column(BigInteger, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey("guilds.id"), nullable=False)
    ctype = Column(Enum(Container), nullable=False)
    exception = Column(Boolean, nullable=False)

    guild = relationship("Guilds", back_populates="guild_rules")

    __table_args__ = (
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

    async def insert_guild(self, guild_id: int, config: Optional[dict] = None):
        new_guild = Guilds(id=guild_id, config=config)
        self.s.add(new_guild)
        await self.s.commit()

    async def get_guild_config(self, guild_id: int) -> Optional[dict]:
        stmt = select(Guilds.config).where(Guilds.id == guild_id)
        result = await self.s.execute(stmt)
        config = result.scalar_one_or_none()
        return config if config else None

    async def get_guild_config_item(
        self, guild_id: int, key: str
    ) -> Optional[Union[bool, str, int]]:
        config = await self.get_guild_config(guild_id)
        return config.get(key, None) if config else None

    async def get_user_config(self, user_id: int) -> Optional[dict]:
        raise NotImplementedError

    async def get_user_config_item(
        self, guild_id: int, key: str
    ) -> Optional[Union[bool, str, int]]:
        raise NotImplementedError

    async def insert_user_rule(
        self,
        id: int,
        user_id: int,
        ctype: Container,
        exception: bool,
    ):
        stmt = (
            insert(UserRules)
            .values(
                id=id,
                user_id=user_id,
                ctype=ctype,
                exception=exception,
            )
            .on_conflict_do_nothing()
        )
        await self.s.execute(stmt)
        await self.s.commit()

    async def delete_user_rule(self, id: int, user_id: int, ctype: Container):
        stmt = select(UserRules).where(
            (UserRules.id == id)
            & (UserRules.user_id == user_id)
            & (UserRules.ctype == ctype)
        )
        result = await self.s.execute(stmt)
        user_rule = result.scalar_one_or_none()

        if user_rule:
            await self.s.delete(user_rule)
            await self.s.commit()

    async def list_user_rules(
        self, user_id: int
    ) -> Tuple[Dict[Container, Set[int]], Dict[Container, Set[int]]]:
        stmt = select(UserRules).where(UserRules.user_id == user_id)
        result = await self.s.execute(stmt)
        user_rules = result.scalars().all()

        rules = {val: set() for val in Container}
        exceptions = {val: set() for val in Container}

        for rule in user_rules:
            cast(int, rule.id)
            cast(Container, rule.ctype)
            exceptions[rule.ctype].add(rule.id) if rule.exception else rules[
                rule.ctype
            ].add(rule.id)

        return rules, exceptions

    async def insert_guild_rule(
        self,
        id: int,
        guild_id: int,
        ctype: Container,
        exception: bool,
    ):
        stmt = (
            insert(GuildRules)
            .values(
                id=id,
                guild_id=guild_id,
                ctype=ctype,
                exception=exception,
            )
            .on_conflict_do_nothing()
        )
        await self.s.execute(stmt)
        await self.s.commit()

    async def delete_guild_rule(self, guild_id: int, id: int, ctype: Container):
        stmt = select(GuildRules).where(
            (GuildRules.id == id)
            & (GuildRules.guild_id == guild_id)
            & (GuildRules.ctype == ctype)
        )
        result = await self.s.execute(stmt)
        guild_rule = result.scalar_one_or_none()

        if guild_rule:
            await self.s.delete(guild_rule)
            await self.s.commit()

    async def list_guild_rules(
        self, guild_id: int
    ) -> Tuple[Dict[Container, Set[int]], Dict[Container, Set[int]]]:
        stmt = select(GuildRules).where(GuildRules.guild_id == guild_id)
        result = await self.s.execute(stmt)
        guild_rules = result.scalars().all()

        # guilds cannot have guild rules
        rules = {val: set() for val in Container if val != Container.GUILD}
        exceptions = {val: set() for val in Container if val != Container.GUILD}

        for rule in guild_rules:
            assert rule.ctype != Container.GUILD
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
