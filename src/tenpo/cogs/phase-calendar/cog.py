# STL
from typing import cast

# PDM
from discord import Bot, Cog, ApplicationContext
from discord.ext import tasks, commands

# LOCAL
from tenpo.types import MessageableGuildChannel
from tenpo.__main__ import DB
from tenpo.log_utils import getLogger
from tenpo.phase_utils import current_emoji, is_major_phase

LOG = getLogger()


class CogPhaseCalendar(Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        self.moon_calendar.start()

    @tasks.loop(minutes=30)
    async def moon_calendar(self):
        LOG.info(type(DB))
        LOG.info("Checking moon calendar")
        title = "mun tenpo"
        if is_major_phase():
            title = "o toki pona taso"
        phase_emoji = current_emoji()
        title = f"{phase_emoji} {title}"

        moon_channels = await DB.get_calendars()
        LOG.debug(moon_channels)
        for channel_id in moon_channels:
            assert isinstance(channel_id, int)
            channel = cast(MessageableGuildChannel, self.bot.get_channel(channel_id))

            if not channel:
                LOG.warning("Channel %s not found in cache", channel)
                try:
                    channel = cast(
                        MessageableGuildChannel,
                        await self.bot.fetch_channel(channel_id),
                    )
                except discord.errors.NotFound:
                    # NOTE: o weka ala tan ilo awen tan ni:
                    # ilo Siko li ken pakala li ken pana ala e tomo.
                    # taso tomo li ken awen lon.
                    LOG.warning("Channel %s not found in cache or on request", channel)
                    continue

            await channel.edit(name=title)
            LOG.info("Updated channel %s", channel)
