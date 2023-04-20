# STL
import sys
import logging
import contextlib
from io import StringIO
from typing import List, Optional

# PDM
import discord
from discord import commands
from discord.ext import commands
from discord.commands import option
from discord.ext.commands import Cog
from discord.commands.context import ApplicationContext

# LOCAL
from tenpo.chat_utils import chunk_response, codeblock_wrap

LOG = logging.getLogger("tenpo")


@contextlib.contextmanager
def stdoutIO(stdout=None):
    old = sys.stdout
    if stdout is None:
        stdout = StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old


async def safe_respond(ctx: ApplicationContext, resp: Optional[str]):
    if not resp:
        resp = "No response."
    chunked = chunk_response(resp)
    try:
        for chunk in chunked:
            chunk = codeblock_wrap(chunk)
            await ctx.respond(chunk)
    except discord.errors.HTTPException:
        await ctx.respond("Something went wrong when responding!")


class CogDebug(Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.is_owner()
    @commands.slash_command(name="ping", help="Ping the bot.")
    async def ping(self, ctx: ApplicationContext):
        await ctx.respond("Pong!")

    @commands.is_owner()
    @commands.slash_command(name="eval", help="Evaluate a given line of code.")
    @option(name="text", required=True)
    async def eval(self, ctx: ApplicationContext, text: str):
        LOG.info("Evaluating: %s", text)
        try:
            response = eval(text)
        except Exception as e:
            response = repr(e)

        await safe_respond(ctx, response)

    @commands.is_owner()
    @commands.slash_command(name="exec", help="Execute a given program.")
    @option(name="text", required=True)
    async def exec(self, ctx: ApplicationContext, text: str):
        LOG.info("Executing: %s", text)
        with stdoutIO() as s:
            try:
                exec(text)
                response = s.getvalue()
            except Exception as e:
                response = repr(e)

        await safe_respond(ctx, response)
