# PDM
import discord
from discord import Bot, User, Member, Thread
from discord.ext import commands
from discord.message import Message
from discord.reaction import Reaction
from discord.ext.commands import Cog

# LOCAL
from tenpo.log_utils import getLogger
from tenpo.str_utils import chunk_response, codeblock_wrap

LOG = getLogger()


async def send_dm_to_user(user: User | Member, message: str):
    if not (dm := user.dm_channel):
        dm = await user.create_dm()

    try:
        _ = await dm.send(message)
    except discord.errors.Forbidden:
        LOG.error("Cannot DM user %s", user.name)
    except discord.errors.HTTPException as e:
        LOG.error("Couldn't send DM due to unexpected exception!")
        LOG.error(f"Error code: {e.code}")
        LOG.error(f"Error text: {e.text}")


async def send_delete_dm(message: Message):
    await send_dm_to_user(
        message.author,
        f"""sina toki pona ala la mi weka e toki sina ni:
{codeblock_wrap(message.content)}
{message.jump_url}
sina wile ala e weka la o kepeken `/lawa nasin`""",
    )


# TODO: link message
async def send_react_error_dm(message: Message, react: str):
    await send_dm_to_user(
        message.author,
        f"""mi alasa sitelen e toki sina ni:
{codeblock_wrap(message.content)}
mi alasa kepeken sitelen ni, taso mi ken ala:
{codeblock_wrap(react)}""",
    )
