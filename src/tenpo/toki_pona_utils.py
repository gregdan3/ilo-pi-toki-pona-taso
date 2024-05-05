# STL
from copy import deepcopy

# PDM
from sonatoki.ilo import Ilo
from sonatoki.Configs import DiscordConfig
from sonatoki.Preprocessors import (
    Spoilers,
    Backticks,
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
        SingleQuotes,
        DoubleQuotes,
        ArrowQuote,
    ]
)

ILO = Ilo(**CONFIG)


def is_toki_pona(s: str):
    return ILO.is_toki_pona(s)
