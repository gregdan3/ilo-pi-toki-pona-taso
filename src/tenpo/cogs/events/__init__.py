# LOCAL
from .cog import CogEvents


def setup(bot):
    bot.add_cog(CogEvents(bot))
