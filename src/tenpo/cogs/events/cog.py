# STL
import logging

# PDM
from discord.guild import Guild
from discord.channel import TextChannel
from discord.ext.commands import Cog, slash_command
from discord.commands.context import ApplicationContext

# LOCAL
from tenpo.__main__ import DB
from tenpo.phase_utils import major_phases_from_now

LOG = logging.getLogger("tenpo")


NEW_MOON_DESC = """mun suli li pimeja ale la o toki pona taso!
the moon is fully dark, so only speak toki pona!
"""
FULL_MOON_DESC = """mun suli li suno ale la o toki pona taso!
the moon is fully lit, so only speak toki pona!
"""

DESCRIPTIONS = {"new": NEW_MOON_DESC, "full": FULL_MOON_DESC}


class CogEvents(Cog):
    def __init__(self, bot):
        self.bot = bot

    # @slash_command(name="setup_events")
    async def slash_setup(self, ctx: ApplicationContext, limit: int = 3):
        await setup_events(ctx, limit)
        await ctx.respond(content="Set up events!", ephemeral=True)


async def setup_events(ctx: ApplicationContext, limit: int = 3):
    guild: Guild = ctx.guild
    channel: TextChannel = ctx.channel

    if not isinstance(channel, TextChannel):
        return

    starts = [event.start_time for event in guild.scheduled_events if event.start_time]

    for time, phase in major_phases_from_now(limit):
        LOG.info("Constructing event for phase %s at time %s", phase, time)
