# STL
import random
from typing import Tuple, Optional, cast

# PDM
from discord import Guild, Member, Thread
from discord.ext import commands
from discord.message import Message
from discord.ext.commands import Cog
from discord.types.channel import Channel

# LOCAL
from tenpo.db import Container
from tenpo.__main__ import DB
from tenpo.log_utils import getLogger
from tenpo.chat_utils import DEFAULT_REACTS
from tenpo.phase_utils import is_major_phase
from tenpo.cogs.rules.cog import MessageableGuildChannel
from tenpo.toki_pona_utils import is_toki_pona

LOG = getLogger()


async def get_guild_role(guild_id: int):
    g_role = await DB.get_role(guild_id)
    return g_role


def user_has_role(user: Member, role: int) -> bool:
    return not not user.get_role(role)
    # yes really, faster than bool for no reason
    # plus it's funny


async def has_disabled(eid: int):
    check = await DB.get_disabled(eid)
    return check


async def in_checked_channel_guild(
    channel_id: int, category_id: Optional[int], guild_id: int
):
    rules, exceptions = await DB.list_rules(guild_id)
    return await in_checked_channel(
        rules, exceptions, channel_id, category_id, guild_id
    )


async def in_checked_channel_user(
    user_id: int,
    channel_id: int,
    category_id: Optional[int],
    guild_id: int,
):
    rules, exceptions = await DB.list_rules(user_id)
    return await in_checked_channel(
        rules, exceptions, channel_id, category_id, guild_id
    )


async def in_checked_channel(
    rules: dict,
    exceptions: dict,
    channel_id: int,
    category_id: Optional[int],
    guild_id: int,
):  # being in rules/exceptions is mutually exclusive
    if channel_id in rules[Container.CHANNEL]:
        return True
    if channel_id in exceptions[Container.CHANNEL]:
        return False

    if category_id in rules[Container.CATEGORY]:
        return True
    if category_id in exceptions[Container.CATEGORY]:
        return False

    if guild_id in rules[Container.GUILD]:
        return True
    # guilds cannot have exceptions

    return False


def startswith_ignorable(message: str, ignorable: list[str]):
    for ignore in ignorable:
        if message.startswith(ignore):
            return True
    return False


class CogOTokiPonaTaso(Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def o_toki_pona_taso(self, message: Message):
        if not await should_check(message):
            LOG.debug("Ignoring message; preconditions failed")
            return

        if not (await should_react_user(message) or await should_react_guild(message)):
            return

        if is_toki_pona(message.content):
            LOG.debug("Ignoring message; is toki pona")
            return

        react = await get_react(message.author.id)
        LOG.debug("Reacting %s to user message" % react)
        await message.add_reaction(react)


async def should_react_user(message: Message) -> bool:
    channel, guild = message.channel, message.guild
    if isinstance(channel, Thread):
        # TODO: configurable thread behavior?
        channel = channel.parent

    if await has_disabled(message.author.id):
        LOG.debug("Ignoring user message; user has disabled")
        return False

    if not await in_checked_channel_user(
        message.author.id,
        channel.id,
        channel.category_id,
        guild.id,
    ):
        LOG.debug("Ignoring user message; not in configured channel")
        return False

    # NOTE: guild rules override this! this is intentional
    opens = await DB.get_opens(message.author.id)
    if startswith_ignorable(message.content, opens):
        LOG.debug("Ignoring user message; starts with ignorable")
        return False

    return True


async def should_react_guild(message: Message) -> bool:
    channel, guild = message.channel, message.guild
    if isinstance(channel, Thread):
        # TODO: configurable thread behavior?
        channel = channel.parent
    if await has_disabled(guild.id):
        LOG.debug("Ignoring guild message; guild has disabled")
        return False

    # TODO: configurable timeframes
    if not is_major_phase():
        LOG.debug("Ignoring guild message; not event time")
        return False

    if role := await get_guild_role(guild.id):
        # if guild set a role, check users with the role; else, check all users
        if not user_has_role(cast(Member, message.author), role):
            LOG.debug("Ignoring guild message; user missing role")
            return False

    if not await in_checked_channel_guild(
        channel.id,
        channel.category_id,
        guild.id,
    ):
        LOG.debug("Ignoring guild message; not in configured channel")
        return False

    return True


async def should_check(message: Message) -> bool:
    """
    Determine if a message is in a location worth checking.
    - The user must not be a bot (see TODO)
    - The message must be in a guild
    - The message must be in a channel
    """
    if message.author.bot:
        # TODO: exclude bots, but not pluralkit? they share a per-server id from the webhook
        # https://pluralkit.me/api/endpoints/#get-proxied-message-information
        return False

    guild = message.guild
    if not guild:
        return False

    # if a message is ever sent in a non-channel, how
    channel = message.channel
    if not channel:
        return False

    return True


async def get_react(eid: int):
    reacts = await DB.get_reacts(eid)
    if reacts:
        return random.choice(reacts)
    return random.choice(DEFAULT_REACTS)
