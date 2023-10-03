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


async def send_delete_dm(message: Message, tan_ma: bool = False):
    resp = f"""toki sina li pona ala la mi weka e ona ni:
{codeblock_wrap(message.content)}\n"""
    if not tan_ma:
        resp += """sina wile ala e weka la o kepeken `/lawa nasin`"""
    else:
        resp += """ni li tan ma la sina ken ala weka"""

    await send_dm_to_user(message.author, resp)


# TODO: link message
async def send_react_error_dm(message: Message, react: str):
    await send_dm_to_user(
        message.author,
        f"""mi alasa sitelen e toki sina ni:
{codeblock_wrap(message.content)}
mi alasa kepeken sitelen ni, taso mi ken ala:
{codeblock_wrap(react)}""",
    )
