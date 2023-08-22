# STL
import random
from typing import Optional, cast

# PDM
import discord
from discord import Bot, User, Member, Thread
from discord.ext import commands
from discord.message import Message
from discord.reaction import Reaction
from discord.ext.commands import Cog

# LOCAL
from tenpo.db import Container
from tenpo.__main__ import DB
from tenpo.log_utils import getLogger
from tenpo.chat_utils import DEFAULT_REACTS, codeblock_wrap
from tenpo.phase_utils import is_major_phase
from tenpo.toki_pona_utils import is_toki_pona

LOG = getLogger()

UNKNOWN_EMOJI_ERR_CODE = 10014


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
    def __init__(self, bot: Bot):
        self.bot: Bot = bot

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

        await respond(message)

    @commands.Cog.listener("on_message_edit")
    async def toki_li_ante_la(self, before: Message, after: Message):
        # NOTE: `on_message_edit` only fires for cached messages
        # *presumably* these are the only kind of messages we care about
        # instead, maybe on_raw_message_edit?
        message = after
        if not await should_check(message):
            LOG.debug("Ignoring edit; preconditions failed")
            return
        if not (await should_react_user(message) or await should_react_guild(message)):
            return

        # check if message already had a react
        # if it had a react, we remove it
        react = await get_own_react(before)
        before_ok = react is None
        after_ok = is_toki_pona(after.content)
        LOG.debug("validity: %s, %s", before_ok, after_ok)

        if before_ok == after_ok:
            LOG.debug("Ignoring edit; did not change validity")
            return
        if before_ok and not after_ok:
            await respond(message)
            return
        if not before_ok and after_ok:
            assert self.bot.user  # asserts we are actually logged in...
            await message.remove_reaction(react, self.bot.user)


async def get_own_react(message: Message) -> Optional[Reaction]:
    for react in message.reactions:
        if react.me:
            return react
    return None


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
    # channel = message.channel
    # if not channel:
    #     return False

    return True


async def respond(message: Message):
    response_type = await DB.get_response(message.author.id)
    await RESPONSE_MAP[response_type](message)

    # react = await get_react(message.author.id)
    # LOG.debug("Reacting %s to user message" % react)
    # await message.add_reaction(react)


async def react_to_msg(message: Message):
    uid = message.author.id
    react = await get_react(uid)
    LOG.debug("Reacting %s to user message" % react)
    try:
        await message.add_reaction(react)
        return
    except discord.errors.HTTPException as e:
        if e.code != UNKNOWN_EMOJI_ERR_CODE:
            LOG.error("Couldn't react due to unexpected exception!")
            LOG.error(f"Error code: {e.code}")
            LOG.error(f"Error text: {e.text}")
            return

    # error handler
    LOG.warning("Couldn't use react %s on user %s", react, message.author.name)
    await send_dm_to_user(
        message.author,
        f"""mi alasa sitelen e toki sina ni:
{codeblock_wrap(message.content)}
mi alasa kepeken sitelen ni, taso mi ken ala:
{codeblock_wrap(react)}""",
    )


async def delete_msg(message: Message):
    LOG.debug("Deleting user message")
    await message.delete(reason="ona o toki pona taso")
    await send_dm_to_user(
        message.author,
        f"""sina toki pona ala la mi weka e toki sina ni:
{codeblock_wrap(message.content)}
sina wile ala e weka la o kepeken `/lawa nasin`""",
    )


async def get_react(eid: int):
    reacts = await DB.get_reacts(eid)
    if reacts:
        return random.choice(reacts)
    return random.choice(DEFAULT_REACTS)


async def send_dm_to_user(user: User | Member, message: str):
    if not (dm := user.dm_channel):
        dm = await user.create_dm()
    await dm.send(message)


RESPONSE_MAP = {
    "sitelen": react_to_msg,
    "weka": delete_msg,
}
