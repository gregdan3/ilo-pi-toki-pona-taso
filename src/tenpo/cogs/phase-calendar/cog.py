# STL
from typing import cast

# PDM
from discord import Bot, Cog
from discord.ext import tasks

# LOCAL
from tenpo.types import MessageableGuildChannel
from tenpo.__main__ import DB
from tenpo.log_utils import getLogger
from tenpo.phase_utils import FACE_MAP, current_emoji, is_major_phase

LOG = getLogger()


def get_calendar_title():
    # TODO: nimi li ken ante
    title = "mun tenpo"
    phase_emoji = current_emoji()
    if is_major_phase():
        phase_emoji = FACE_MAP[phase_emoji]
        title = "o toki pona taso"
    title = f"{phase_emoji} {title}"
    return title


class CogPhaseCalendar(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot: Bot = bot
        _ = self.moon_calendar.start()

    async def fetch_channel(self, channel_id: int) -> MessageableGuildChannel | None:
        assert isinstance(channel_id, int)
        channel = cast(MessageableGuildChannel, self.bot.get_channel(channel_id))
        if channel:
            return channel

        channel = cast(
            MessageableGuildChannel, await self.bot.fetch_channel(channel_id)
        )

        if channel:
            return channel

        return None

    @tasks.loop(minutes=30)
    async def moon_calendar(self):
        title = get_calendar_title()
        moon_channels = await DB.get_calendars()
        LOG.debug(moon_channels)

        channel = None
        channel_id = None
        for channel_id in moon_channels:
            try:
                channel = await self.fetch_channel(channel_id)
                if not channel:
                    continue
                _ = await channel.edit(name=title)
                LOG.info("Updated channel %s to %s", channel_id, channel)

            except Exception as e:
                LOG.error("Got an error while editing channel! %s", e)
                LOG.error("Occurred on channel %s %s", channel_id, channel)
                LOG.error("... %s", e.__dict__)
                LOG.error("Swallowing the error in the hopes of the task surviving.")
                continue
