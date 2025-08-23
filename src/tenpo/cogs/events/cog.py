# PDM
from discord.ext import commands
from discord.guild import Guild
from discord.channel import TextChannel
from discord.ext.commands import Cog, slash_command
from discord.commands.context import ApplicationContext

# LOCAL
from tenpo.__main__ import DB
from tenpo.log_utils import getLogger

LOG = getLogger()

NAME = "tenpo pi toki pona taso"
NEW_MOON_DESC = """mun suli li pimeja ale la o toki pona taso!
the moon is fully dark, so only speak toki pona!
"""
FULL_MOON_DESC = """mun suli li suno ale la o toki pona taso!
the moon is fully lit, so only speak toki pona!
"""
NON_MOON_DESC = """tenpo li kama! o toki pona taso!
the event has arrived! only speak toki pona!"""

DESCRIPTIONS = {
    "new": NEW_MOON_DESC,
    "full": FULL_MOON_DESC,
    "none": NON_MOON_DESC,
}


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

    starts = [
        (event.name, int(event.start_time.timestamp()))
        for event in guild.scheduled_events
        if event.start_time
    ]

    method = await DB.get_timing(guild.id)
    if method == "mun":
        timer = await DB.get_moon_timer(guild.id)
    elif method == "wile":
        timer = await DB.get_event_timer(guild.id)
    else:
        return False

    for start, end in timer.get_events_from():
        LOG.info("Making event from %s to %s", start, end)

        description = DESCRIPTIONS["none"]
        if method == "mun":
            phase = timer.get_phase(ref=start)
            assert phase
            description = DESCRIPTIONS[phase]

        if (NAME, int(start.timestamp())) in starts:
            LOG.warning("Event already scheduled. Not re-creating!")
            continue

        event = await guild.create_scheduled_event(
            name=NAME,
            location=guild.name,
            description=description,
            start_time=start,
            end_time=end,
        )

    return True
