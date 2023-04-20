# LOCAL
from .cog import CogRules


def setup(bot):
    bot.add_cog(CogRules(bot))
