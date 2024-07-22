# PDM
from discord import Bot, User, Member, Thread
from discord.ext import commands
from discord.message import Message
from discord.reaction import Reaction
from discord.ext.commands import Cog

# LOCAL
from tenpo.str_utils import chunk_response, codeblock_wrap


async def send_dm_to_user(user: User | Member, message: str):
    if not (dm := user.dm_channel):
        dm = await user.create_dm()
    await dm.send(message)


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
