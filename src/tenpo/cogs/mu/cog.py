# PDM
from discord import Cog, slash_command
from discord.commands.context import ApplicationContext

# LOCAL
from tenpo.log_utils import getLogger

LOG = getLogger()


class CogMu(Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="mu")
    async def mu(self, ctx: ApplicationContext):
        await ctx.respond("mu")
