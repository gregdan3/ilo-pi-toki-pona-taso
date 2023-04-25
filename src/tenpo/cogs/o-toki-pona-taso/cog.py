# STL
import random
import logging
from typing import Optional

# PDM
import discord
from discord import Thread, DMChannel, TextChannel, ForumChannel
from discord.ext import commands
from discord.message import Message
from discord.ext.commands import Cog
from discord.types.channel import GroupDMChannel

# LOCAL
from tenpo.db import Container
from tenpo.__main__ import DB
from tenpo.phase_utils import is_major_phase
from tenpo.toki_pona_utils import is_toki_pona

LOG = logging.getLogger("tenpo")

EMOJIS = "🌵🌲🌲🌲🌲🌲🌳🌳🌳🌳🌳🌴🌴🌴🌴🌴🌱🌱🌱🌱🌱🌿🌿🌿🌿🌿☘️☘️☘️☘️🍀🍃🍂🍁🌷🌺🌻🐝🐌🐛🐞🦋"
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

    # @commands.Cog.listener("on_message")
    # async def o_toki_pona_taso(self, message: Message):
    #     # fetch user configuration
    #     pass

    @commands.Cog.listener("on_message")
    async def tenpo_la_o_toki_pona_taso(self, message: Message):
        # TODO: combine with user rules so we don't double kasi? hmm or just accept double kasi
        guild = message.guild
        if not guild:
            return

        channel = message.channel
        if isinstance(channel, DMChannel):
            return
        if isinstance(channel, Thread):
            channel = channel.parent

        if message.author.bot:
            # TODO: exclude bots, but not pluralkit? they share a per-server id from the webhook
            # https://pluralkit.me/api/endpoints/#get-proxied-message-information
            return

        if not is_major_phase():
            return

        if not await in_checked_channel_guild(
            channel.id,
            channel.category_id,
            guild.id,
        ):
            return

        if is_toki_pona(message.content):
            return

        LOG.debug("Message %s gets a plant!", message)
        await message.add_reaction(get_emoji())  # TODO: user/guild choose delete/react


def get_emoji():
    return random.choice(EMOJIS)
