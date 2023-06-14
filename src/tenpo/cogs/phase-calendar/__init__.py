# LOCAL
from .cog import CogPhaseCalendar


def setup(bot):
    bot.add_cog(CogPhaseCalendar(bot))
