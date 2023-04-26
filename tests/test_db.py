"""
Test the database on a basic level directly
"""
# STL
import uuid
import asyncio
from datetime import datetime

# PDM
import pytest
from sqlalchemy import select
from sqlalchemy.future import select

# LOCAL
from tenpo.db import Entity, TenpoDB, IconsBanners


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def tenpo_db():
    db = await TenpoDB(":memory:")
    yield db
    await asyncio.shield(db.close())


@pytest.mark.asyncio
async def test_guilds(tenpo_db):
    tenpo_db = await anext(tenpo_db)
    # Create a guild
    new_guild = Entity(id=12345)
    tenpo_db.s.add(new_guild)
    await tenpo_db.s.commit()

    # Query the created guild
    result = await tenpo_db.s.execute(select(Entity).filter_by(id=12345))
    guild = result.scalars().one()
    assert guild.id == 12345
    await tenpo_db.close()


@pytest.mark.asyncio
async def test_icons_banners(tenpo_db):
    tenpo_db = await anext(tenpo_db)
    # Create a guild and icons_banners
    new_guild = Entity(id=13579)
    new_icon_banner = IconsBanners(
        id=uuid.uuid4(),
        guild_id=13579,
        author_id=54321,
        last_used=datetime(year=2023, month=3, day=17),
        name="foo",
        icon=b"icon_data",
        banner=b"banner_data",
    )
    tenpo_db.s.add_all([new_guild, new_icon_banner])
    await tenpo_db.s.commit()

    result = await tenpo_db.s.execute(select(IconsBanners).filter_by(author_id=54321))
    icon_banner = result.scalars().one()
    assert icon_banner.guild.id == 13579
    assert icon_banner.author_id == 54321
    await tenpo_db.close()


def test_users_config_read_write() -> None:
    # Create a Entity instance with a config
    user = Entity(id=1, config={"reacts": ["👍", "👎"]})

    # Test reading the config
    assert user.config == {"reacts": ["👍", "👎"]}

    # Test writing to the config
    user.config["language"] = "English"
    assert user.config == {"reacts": ["👍", "👎"], "language": "English"}

    # Test modifying the config
    user.config["reacts"].append("🎉")
    assert user.config == {"reacts": ["👍", "👎", "🎉"], "language": "English"}
