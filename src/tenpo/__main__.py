# STL
import os
import asyncio
import logging
from typing import Any

# PDM
from dotenv import load_dotenv
from discord import Intents
from discord.ext import commands

# LOCAL
from tenpo.db import TenpoDB
from tenpo.log_utils import getLogger, configure_logger

LOG = getLogger()

load_dotenv()


def load_envvar(envvar: str, default: Any = None) -> str:
    val = os.getenv(envvar)
    if not val:
        if default is not None:
            return default
        else:
            raise EnvironmentError(f"No {envvar} found in environment!")
    return val


TOKEN = load_envvar("DISCORD_TOKEN")
DB_FILE = load_envvar("DB_FILE")
LOG_LEVEL = load_envvar("LOG_LEVEL", "WARNING")
LOG_LEVEL_INT = getattr(logging, LOG_LEVEL.upper())

DEBUG_GUILDS = load_envvar("DEBUG_GUILDS", "")
if DEBUG_GUILDS:
    DEBUG_GUILDS = [int(n) for n in DEBUG_GUILDS.split(",") if n and n.isdigit()]


LOOP = asyncio.new_event_loop()
DB = asyncio.run(TenpoDB(database_file=DB_FILE))
BOT = commands.Bot(
    loop=LOOP,
    command_prefix="/",
    intents=Intents.all(),
    debug_guilds=DEBUG_GUILDS,
)


@BOT.event
async def on_ready():
    for index, guild in enumerate(BOT.guilds):
        LOG.info("{}) {}".format(index + 1, guild.name))


@BOT.event
async def on_reaction_add(reaction, user):
    if reaction.message.author == BOT.user:
        if reaction.emoji == "❌":
            await reaction.message.delete()


def load_extensions():
    cogs_path = os.path.dirname(__file__) + "/cogs/"
    for cogname in sorted(os.listdir(cogs_path), key=len):
        if cogname == "debug":
            if DEBUG_GUILDS:
                LOG.warning("DEBUG_GUILDS set: %s. Loading debug module.", DEBUG_GUILDS)
            else:
                LOG.info("Not loading debug module")
                continue

        path = cogs_path + cogname
        if not os.path.isdir(path):
            continue
        if not ("__init__.py" in os.listdir(path)):
            continue
        LOG.info("Loading cog %s", cogname)
        BOT.load_extension(f"tenpo.cogs.{cogname}")


def main():
    configure_logger("tenpo", log_level=LOG_LEVEL_INT)
    configure_logger("discord", log_level=logging.WARNING)
    load_extensions()
    BOT.run(TOKEN, reconnect=True)


if __name__ == "__main__":
    main()
