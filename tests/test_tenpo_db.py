"""
Test the interface of TenpoDB
"""
# STL
import asyncio
from datetime import datetime

# PDM
import pytest

# LOCAL
from tenpo.db import Guilds, TenpoDB


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
async def test_insert_guild(tenpo_db):
    tenpo_db = await anext(tenpo_db)

    await tenpo_db.insert_guild(123, config={"key": "value"})

    guild = await tenpo_db.s.get(Guilds, 123)
    assert guild.id == 123
    assert guild.config == {"key": "value"}

    await tenpo_db.close()


@pytest.mark.asyncio
@pytest.mark.skip(
    "not been updated since db started tracking default in table instead of config"
)
async def test_set_guild_default_icon_banner(tenpo_db):
    tenpo_db = await anext(tenpo_db)

    # Insert a guild
    guild_id = 123
    await tenpo_db.insert_guild(guild_id)

    # Insert an icon and banner
    icon = b"fake_icon_data"
    banner = b"fake_banner_data"
    name = "example_name"
    author_id = 456
    config = {"key": "value"}
    last_used = datetime.now()

    uuid1 = await tenpo_db.insert_icon_banner(
        guild_id, author_id, name, last_used, config, icon, banner
    )

    # Update the guild's default icon and banner
    await tenpo_db.set_default_icon_banner(guild_id, name)

    # Verify the update
    guild_config = await tenpo_db.get_guild_config(guild_id)
    assert guild_config["default_icon_banner"] == str(uuid1)

    await tenpo_db.close()


@pytest.mark.asyncio
async def test_get_icon_banner_by_name(tenpo_db):
    tenpo_db = await anext(tenpo_db)

    # Insert a new icon/banner
    guild_id = 12345
    author_id = 67890
    name = "test_banner"
    icon = b"icon_data"
    banner = b"banner_data"
    config = {"key": "value"}
    last_used = datetime.now()

    uuid = await tenpo_db.insert_icon_banner(
        guild_id=guild_id,
        author_id=author_id,
        name=name,
        last_used=last_used,
        config=config,
        icon=icon,
        banner=banner,
    )

    # Fetch the icon/banner by name
    fetched_banner = await tenpo_db.get_icon_banner_by_name(guild_id, name)

    # Assertions
    assert fetched_banner is not None
    assert fetched_banner.guild_id == guild_id
    assert fetched_banner.author_id == author_id
    assert fetched_banner.name == name
    assert fetched_banner.last_used == last_used
    assert fetched_banner.icon == icon
    assert fetched_banner.banner == banner

    await tenpo_db.close()
