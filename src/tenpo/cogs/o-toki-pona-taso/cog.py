# STL
import random
from typing import Any, Optional, cast

# PDM
import discord
from discord import Bot, Member, Thread, MessageType, AllowedMentions
from discord.ext import commands
from discord.message import Message
from discord.reaction import Reaction
from discord.ext.commands import Cog

# LOCAL
from tenpo.types import DiscordContainer
from tenpo.__main__ import DB
from tenpo.log_utils import getLogger
from tenpo.str_utils import prep_msg_for_resend
from tenpo.chat_utils import send_delete_dm, send_react_error_dm
from tenpo.toki_pona_utils import is_toki_pona

LOG = getLogger()

UNKNOWN_EMOJI_ERR_CODE = 10014
RESEND_MENTIONS = AllowedMentions(
    everyone=False, users=False, roles=False, replied_user=False
)

ALLOWED_MESSAGE_TYPES = {
    MessageType.default,
    MessageType.reply,
}


def user_has_role(user: Member, role: int) -> bool:
    return not not user.get_role(role)
    # yes really, faster than bool for no reason
    # plus it's funny


class CogOTokiPonaTaso(Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        super().__init__()

    @commands.Cog.listener("on_message")
    async def o_toki_pona_taso(self, message: Message):
        if await should_respond(message):
            await respond(message)

    @commands.Cog.listener("on_message_edit")
    async def toki_li_ante_la(self, before: Message, after: Message):
        # TODO: switch to message cache in the future
        # in case future responses no longer react
        react = await get_own_react(before)
        resp_before = react is not None
        resp_after = await should_respond(after)

        if resp_before == resp_after:
            return
        if not resp_before and resp_after:
            await respond(after)
            return
        if resp_before and not resp_after:
            assert self.bot.user  # asserts we are actually logged in...
            await after.remove_reaction(react, self.bot.user)


async def should_check(message: Message) -> bool:
    """
    Determine if a message is worth checking.
    - The user must not be a bot (see TODO)
    - The message must be in a guild
    - The message must be in a channel
    - The message must be from the last 1hr (see TODO)
    """
    if message.author.bot:
        # TODO: exclude bots, but not pluralkit? they share a per-server id from the webhook
        # https://pluralkit.me/api/endpoints/#get-proxied-message-information
        return False

    guild = message.guild
    if not guild:
        return False

    msg_type = message.type
    if msg_type not in ALLOWED_MESSAGE_TYPES:
        return False

    # if a message is ever sent in a non-channel, how
    # channel = message.channel
    # if not channel:
    #     return False

    # TODO: if a message is from >1hr ago, we don't care anymore

    return True


async def should_check_user(message: Message) -> bool:
    channel, guild, author = message.channel, message.guild, message.author
    if await DB.get_disabled(author.id):
        LOG.debug("Ignoring user message; disabled")
        return False

    if await DB.is_sleeping(author.id):
        LOG.debug("Ignoring user message; sleeping")
        return False

    channel_id = channel.parent_id if isinstance(channel, Thread) else channel.id
    thread_id = channel.id if isinstance(channel, Thread) else None
    if not await DB.in_checked_channel(
        author.id,
        thread_id,
        channel_id,
        channel.category_id,
        guild.id,
    ):
        LOG.debug("Ignoring user message; not in configured channel")
        return False

    # NOTE: guild rules override this! this is intentional
    if await DB.startswith_ignorable(author.id, message.content):
        LOG.debug("Ignoring user message; starts with ignorable")
        return False

    return True


async def should_check_guild(message: Message) -> bool:
    channel, guild, author = message.channel, message.guild, message.author
    assert guild
    if await DB.get_disabled(guild.id):
        LOG.debug("Ignoring guild message; disabled")
        return False

    if await DB.is_sleeping(guild.id):
        LOG.debug("Ignoring guild message; sleeping")
        return False

    if not await DB.is_event_time(guild.id):
        LOG.debug("Ignoring guild message; not event time")
        return False

    # if guild set a role, check users with the role; else, check all users
    if role := await DB.get_role(guild.id):
        if not user_has_role(cast(Member, author), role):
            LOG.debug("Ignoring guild message; user missing role")
            return False

    channel_id = channel.parent_id if isinstance(channel, Thread) else channel.id
    thread_id = channel.id if isinstance(channel, Thread) else None
    if not await DB.in_checked_channel(
        guild.id,
        thread_id,
        channel_id,
        channel.category_id,
        guild.id,
    ):
        LOG.debug("Ignoring guild message; not in checked channel")
        return False

    return True


async def should_respond(message: Message) -> bool:
    if not await should_check(message):
        LOG.debug("Ignoring message; preconditions failed")
        return False

    if await should_check_guild(message):
        spoilers = await DB.get_spoilers(message.guild.id)
        if not is_toki_pona(message.content, spoilers=spoilers):
            return True

    if await should_check_user(message):
        spoilers = await DB.get_spoilers(message.author.id)
        if not is_toki_pona(message.content, spoilers=spoilers):
            return True

    return False


async def get_react(eid: int):
    reacts = await DB.get_reacts(eid)
    return random.choice(reacts)


async def react_message(message: Message):
    uid = message.author.id

    iters = 5
    while iters > 0:
        iters -= 1
        react = await get_react(uid)

        try:
            await message.add_reaction(react)
            LOG.debug("Reacted %s to user message" % react)
            return

        except discord.errors.Forbidden as e:
            LOG.warning("Couldn't react to user message; disallowed. Deleting instead!")
            await resend_message(message)
            # fallback since user may have blocked bot
            return
        except discord.errors.NotFound as e:
            LOG.warning("Couldn't react to user message; not found.")
            return
        except discord.errors.HTTPException as e:
            LOG.warning("Couldn't react %s to user %s", react, message.author.name)
            await send_react_error_dm(message, react)
            result = await DB.delete_react(uid, react)
            # loop

    # TODO: i should probably inform user if we get here.
    # but also, fuck's sake, what


async def delete_message(message: Message, dm: bool = True):
    LOG.debug("Deleting user message")
    try:
        await message.delete(reason="o toki pona taso")
        if dm:
            await send_delete_dm(message)
    except discord.errors.Forbidden:
        LOG.warning("Couldn't delete message; disallowed")
    except discord.errors.NotFound:
        LOG.warning("Couldn't delete message; not found")
    except discord.errors.HTTPException as e:
        LOG.error("Couldn't delete message; reason unknown")
        LOG.error(f"Error code: {e.code}")
        LOG.error(f"Error text: {e.text}")


async def resend_message(message: Message):
    reply = prep_msg_for_resend(message.content, message.author.id)

    kwargs: dict[Any, Any] = {
        "suppress": True,
        "allowed_mentions": RESEND_MENTIONS,
    }

    if message.reference:
        kwargs["reference"] = message.reference

    # if message.attachments:
    #     ex = message.attachments[0]
    #     ex.waveform
    #     kwargs["file"] =

    # we will resend, so no DM needed
    await delete_message(message, dm=False)
    try:
        _ = await message.channel.send(reply, **kwargs)
    except discord.errors.Forbidden:
        LOG.error("Couldn't re-send message; disallowed")
    except discord.errors.HTTPException as e:
        LOG.error("Couldn't re-send message due to unexpected exception!")
        LOG.error(f"Error code: {e.code}")
        LOG.error(f"Error text: {e.text}")


async def respond(message: Message):
    response_type = await DB.get_response(message.author.id)
    await RESPONSE_MAP[response_type](message)


async def get_own_react(message: Message) -> Optional[Reaction]:
    for react in message.reactions:
        if react.me:
            return react
    return None


RESPONSE_MAP = {
    "sitelen": react_message,
    "weka": delete_message,
    "len": resend_message,
    "sitelen lili": react_message,  # TODO: version of this that is cache-aware
}
