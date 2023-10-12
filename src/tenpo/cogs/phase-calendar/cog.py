# STL
from typing import cast

# PDM
import discord
from discord import Bot, Cog
from discord.ext import tasks

# LOCAL
from tenpo.types import MessageableGuildChannel
from tenpo.__main__ import DB
from tenpo.log_utils import getLogger
from tenpo.phase_utils import current_emoji, is_major_phase

LOG = getLogger()


def get_calendar_title():
    # TODO: nimi li ken ante
    title = "mun tenpo"
    if is_major_phase():
        title = "o toki pona taso"
    phase_emoji = current_emoji()
    title = f"{phase_emoji} {title}"
    return title


class CogPhaseCalendar(Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        self.moon_calendar.start()

    @tasks.loop(minutes=30)
    async def moon_calendar(self):
        title = get_calendar_title()

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
                except discord.errors.Forbidden:
                    LOG.warning("Channel %s no longer accessible.", channel)
                    continue
                except discord.errors.NotFound:
                    # NOTE: o weka ala tan ilo awen tan ni:
                    # ilo Siko li ken pakala li ken pana ala e tomo.
                    # taso tomo li ken awen lon.
                    LOG.warning("Channel %s not found in cache or on request", channel)
                    continue
                except Exception as e:
                    LOG.critical("Got an unknown error while fetching channel! %s", e)
                    LOG.critical("Occurred on channel %s %s", channel_id, channel)
                    LOG.critical("... %s", e.__dict__)
                    LOG.critical("The moon calendar task will now die.")
                    # TODO: o toki tawa mi
                    raise e
            try:
                await channel.edit(name=title)
            except discord.errors.Forbidden:
                LOG.warning("Unable to edit channel %s. No permission?", channel_id)
            except Exception as e:
                LOG.critical("Got an unknown error while editing channe! %s", e)
                LOG.critical("Occurred on channel %s %s", channel_id, channel)
                LOG.critical("... %s", e.__dict__)
                LOG.critical("The moon calendar task will now die.")
                # TODO: o toki tawa mi
                raise e

            LOG.info("Updated channel %s to %s", channel_id, channel)
