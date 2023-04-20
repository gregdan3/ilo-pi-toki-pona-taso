# LOCAL
from .cog import CogDebug


def setup(bot):
    bot.add_cog(CogDebug(bot))
