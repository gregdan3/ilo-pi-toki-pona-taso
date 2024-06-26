# STL
from copy import deepcopy

# PDM
from sonatoki.ilo import Ilo
from sonatoki.Configs import DiscordConfig
from sonatoki.Preprocessors import (
    Spoilers,
    Backticks,
    Reference,
    ArrowQuote,
    DoubleQuotes,
    SingleQuotes,
    DiscordEmotes,
)

EMOTES_RE = DiscordEmotes.pattern.pattern

CONFIG = deepcopy(DiscordConfig)
CONFIG["preprocessors"].extend(
    [
        Backticks,
        Spoilers,
        Reference,
        # SingleQuotes,
        # DoubleQuotes,
        ArrowQuote,
    ]
)
CONFIG["passing_score"] = 0.8

ILO = Ilo(**CONFIG)


def is_toki_pona(s: str):
    return ILO.is_toki_pona(s)
