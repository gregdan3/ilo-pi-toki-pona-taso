# LOCAL
from .cog import CogMu


def setup(bot):
    bot.add_cog(CogMu(bot))
