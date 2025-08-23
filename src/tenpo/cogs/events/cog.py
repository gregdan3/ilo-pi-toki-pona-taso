# STL
import datetime

# PDM
from discord.ext import commands
from discord.guild import Guild
from discord.channel import TextChannel
from discord.ext.commands import Cog, slash_command
from discord.commands.context import ApplicationContext

# LOCAL
from tenpo.__main__ import DB
from tenpo.log_utils import getLogger
from tenpo.phase_utils import major_phases_from_now

LOG = getLogger()

NAME = "tenpo pi toki pona taso"
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

    @slash_command(name="setup_events")
    @commands.has_permissions(manage_channels=True)
    async def slash_setup(self, ctx: ApplicationContext, limit: int = 3):
        await setup_events(ctx, limit)
        await ctx.respond(content="Set up events!", ephemeral=True)


async def setup_events(ctx: ApplicationContext, limit: int = 3):
    # TODO: this should be a repeating event that checks the server for set configuration
    guild: Guild = ctx.guild
    channel: TextChannel = ctx.channel

    if not isinstance(channel, TextChannel):
        return

    starts = [
        (event.name, event.start_time.timestamp())
        for event in guild.scheduled_events
        if event.start_time
    ]

    for dtime, phase in major_phases_from_now(limit):
        dtime = dtime.utc_datetime()
        LOG.info("Constructing event for phase %s at time %s", phase, dtime)

        if (NAME, dtime.timestamp()) in starts:
            LOG.warning("Event already scheduled. Not re-creating!")
            continue

        # Create the event in the guild
        event = await guild.create_scheduled_event(
            name=NAME,
            location=guild.name,
            description=DESCRIPTIONS[phase],
            start_time=dtime,
            end_time=dtime + datetime.timedelta(hours=24),
            # image=image,  # TODO: add images
        )
