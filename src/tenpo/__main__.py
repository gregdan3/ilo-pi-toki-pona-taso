# STL
import os
import logging

# PDM
from dotenv import load_dotenv
from discord import Intents
from discord.ext import commands
from ilo.log_config import configure_logger

LOG = logging.getLogger("ilo")

# from discord import Intents


TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise EnvironmentError("No discord token found in the environment!")

LOG_LEVEL = os.getenv("LOG_LEVEL")
if not LOG_LEVEL:
    LOG_LEVEL = "INFO"

TEST_SERVERS = os.getenv("TEST_SERVERS")
if TEST_SERVERS:
    TEST_SERVERS = TEST_SERVERS.split(",")

LOG_LEVEL_INT = getattr(logging, LOG_LEVEL.upper())

bot = commands.Bot(
    command_prefix="/",
    intents=Intents.all(),
)


@bot.event
async def on_ready():
    for index, guild in enumerate(bot.guilds):
        print("{}) {}".format(index + 1, guild.name))


@bot.event
async def on_reaction_add(reaction, user):
    if reaction.message.author == bot.user:
        if reaction.emoji == "❌":
            await reaction.message.delete()


def load_extensions():
    cogs_path = os.path.dirname(__file__) + "/cogs/"
    for cogname in sorted(os.listdir(cogs_path), key=len):
        path = cogs_path + cogname
        if os.path.isdir(path):
            if "__init__.py" in os.listdir(path):
                LOG.info("Loading cog %s", cogname)
                bot.load_extension(f"ilo.cogs.{cogname}")


if __name__ == "__main__":
    configure_logger("ilo", log_level=LOG_LEVEL_INT)
    configure_logger("discord", log_level=logging.WARNING)
    load_extensions()
    bot.run(TOKEN, reconnect=True)

if __name__ == "__main__":
    main()
