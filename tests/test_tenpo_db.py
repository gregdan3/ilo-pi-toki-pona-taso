"""
Test the interface of TenpoDB
"""
# STL
import asyncio
from typing import List
from datetime import datetime

# PDM
import pytest
from sqlalchemy import text, select, update

# LOCAL
from tenpo.db import Entity, TenpoDB, ConfigKey


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


@pytest.mark.skip("dunders cannot be tested by their name")
@pytest.mark.asyncio
async def test_get_entity(tenpo_db) -> None:
    tenpo_db = await anext(tenpo_db)

    # Add a user to the database
    user = Entity(id=1, config={"language": "English"})
    tenpo_db.s.add(user)
    await tenpo_db.s.commit()

    # Test the case when the entity exists
    entity = await tenpo_db.__get_entity(1)
    assert entity is not None
    assert entity.id == 1

    # Test the case when the entity doesn't exist
    non_existent_eid = 99999
    entity = await tenpo_db.__get_entity(non_existent_eid)
    assert entity is not None
    assert entity.id == non_existent_eid
    assert entity.config == {}


@pytest.mark.asyncio
@pytest.mark.skip("not updated since db rewrite but relevant to future db")
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


@pytest.mark.asyncio
async def test_get_reacts_empty(tenpo_db) -> None:
    tenpo_db = await anext(tenpo_db)

    # No reacts should be set by default
    reacts = await tenpo_db.get_reacts(1)
    assert reacts is None


@pytest.mark.asyncio
async def test_get_reacts_user(tenpo_db) -> None:
    tenpo_db = await anext(tenpo_db)

    # Set reacts directly in the database
    user = Entity(id=1, config={"reacts": ["👍", "👎"]})
    tenpo_db.s.add(user)
    await tenpo_db.s.commit()

    # Test get_reacts
    reacts = await tenpo_db.get_reacts(1)
    assert reacts == ["👍", "👎"]


@pytest.mark.asyncio
async def test_get_reacts_guild(tenpo_db) -> None:
    tenpo_db = await anext(tenpo_db)

    # Set reacts directly in the database
    guild = Entity(id=1, config={"reacts": ["🎉", "😄"]})
    tenpo_db.s.add(guild)
    await tenpo_db.s.commit()

    # Test get_reacts
    reacts = await tenpo_db.get_reacts(1)
    assert reacts == ["🎉", "😄"]


@pytest.mark.asyncio
async def test_set_get_reacts_directly(tenpo_db) -> None:
    tenpo_db = await anext(tenpo_db)

    # Set reacts using the set_reacts method
    await tenpo_db.set_reacts(1, ["👍", "👎"])

    # Read the data directly from the tenpo_db.s session
    stmt = select(Entity).where(Entity.id == 1)
    result = await tenpo_db.s.execute(stmt)
    user = result.scalar_one_or_none()

    # Check the reacts
    assert user is not None
    assert user.config["reacts"] == ["👍", "👎"]


@pytest.mark.asyncio
async def test_set_get_reacts(tenpo_db) -> None:
    tenpo_db = await anext(tenpo_db)

    guild_reacts = ["🎉", "❤️", "🚀"]
    await tenpo_db.set_reacts(1, guild_reacts)
    fetched_guild_reacts = await tenpo_db.get_reacts(1)
    assert fetched_guild_reacts == guild_reacts


@pytest.mark.asyncio
async def test_get_opens(tenpo_db) -> None:
    tenpo_db = await anext(tenpo_db)

    opens: List[str] = ["channel1", "channel2"]
    await tenpo_db._TenpoDB__set_config_item(1, ConfigKey.OPENS, opens)

    saved_opens = await tenpo_db.get_opens(1)
    assert saved_opens == opens


@pytest.mark.asyncio
async def test_toggle_open(tenpo_db) -> None:
    tenpo_db = await anext(tenpo_db)

    open_channel: str = "channel1"
    await tenpo_db._TenpoDB__set_config_item(1, ConfigKey.OPENS, [])

    added = await tenpo_db.toggle_open(1, open_channel)
    assert added

    saved_opens = await tenpo_db.get_opens(1)
    assert saved_opens == [open_channel]

    removed = await tenpo_db.toggle_open(1, open_channel)
    assert not removed

    saved_opens = await tenpo_db.get_opens(1)
    assert saved_opens == []
