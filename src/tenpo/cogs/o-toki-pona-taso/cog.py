# STL
import random
from typing import Tuple, Optional

# PDM
from discord import Guild, Thread
from discord.ext import commands
from discord.message import Message
from discord.ext.commands import Cog
from discord.types.channel import Channel

# LOCAL
from tenpo.db import Owner, Container
from tenpo.__main__ import DB
from tenpo.log_utils import getLogger
from tenpo.chat_utils import DEFAULT_REACTS
from tenpo.phase_utils import is_major_phase
from tenpo.toki_pona_utils import is_toki_pona

LOG = getLogger()

# TODO: add to Guild/user config?


async def in_checked_channel_guild(
    channel_id: int, category_id: Optional[int], guild_id: int
):
    rules, exceptions = await DB.list_rules(guild_id, Owner.GUILD)
    return await in_checked_channel(
        rules, exceptions, channel_id, category_id, guild_id
    )


async def in_checked_channel_user(
    user_id: int,
    channel_id: int,
    category_id: Optional[int],
    guild_id: int,
):
    rules, exceptions = await DB.list_rules(user_id, Owner.USER)
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


class CogOTokiPonaTaso(Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def o_toki_pona_taso(self, message: Message):
        if not (package := await should_check(message)):
            return
        guild, channel = package

        if not await in_checked_channel_user(
            message.author.id,
            channel.id,  # type: ignore
            channel.category_id,  # type: ignore
            guild.id,
        ):
            return

        if is_toki_pona(message.content):
            return

        react = await get_react(message.author.id, Owner.USER)
        await message.add_reaction(react)

    @commands.Cog.listener("on_message")
    async def tenpo_la_o_toki_pona_taso(self, message: Message):
        if (package := await should_check(message)) is None:
            return
        guild, channel = package

        if not is_major_phase():
            return

        if not await in_checked_channel_guild(
            channel.id,  # type: ignore
            channel.category_id,  # type: ignore
            guild.id,
        ):
            return

        if is_toki_pona(message.content):
            return

        react = await get_react(message.author.id, Owner.USER)
        # guild can't choose their own reacts... TODO: ?
        await message.add_reaction(react)


async def should_check(message: Message) -> Optional[Tuple[Guild, Channel]]:
    """Determine if a message is in a location and by a user worth checking for TPT
    Does not check rules or time
    Return message's guild, channel to check, or None if no check should be performed
    """
    if message.author.bot:
        # TODO: exclude bots, but not pluralkit? they share a per-server id from the webhook
        # https://pluralkit.me/api/endpoints/#get-proxied-message-information
        return

    guild = message.guild
    if not guild:
        return

    channel = message.channel

    # if a message is ever sent in a non-channel, how
    # if not channel:
    #     return

    # redundant to guild check, but pyright will errantly complain
    # if not isinstance(channel, MessageableGuildChannel):
    #     return

    if isinstance(channel, Thread):
        channel = channel.parent

    return guild, channel  # type: ignore


async def get_react(owner_id: int, owner_type: Owner):
    reacts = await DB.get_reacts(owner_id, owner_type)
    if reacts:
        return random.choice(reacts)
    return random.choice(DEFAULT_REACTS)
