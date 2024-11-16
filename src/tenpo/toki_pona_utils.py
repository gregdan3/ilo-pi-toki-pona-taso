# STL
from copy import deepcopy

# PDM
from sonatoki.ilo import Ilo
from sonatoki.Configs import PrefConfig
from sonatoki.Preprocessors import (
    URLs,
    Emoji,
    Emails,
    Spoilers,
    Backticks,
    Reference,
    ArrowQuote,
    MarkdownURLs,
    DiscordEmotes,
    DiscordSpecial,
    DiscordChannels,
    DiscordMentions,
    AngleBracketObject,
)

EMOTES_RE = DiscordEmotes.pattern.pattern

CONFIG = deepcopy(PrefConfig)
CONFIG["preprocessors"] = [
    # roughly ordered by permissivity
    Backticks,
    Spoilers,
    # ArrowQuote,
    # AngleBracketObject,
    Reference,
    MarkdownURLs,
    DiscordEmotes,
    DiscordMentions,
    DiscordChannels,
    DiscordSpecial,
    URLs,
    Emails,
    Emoji,
]

ILO = Ilo(**CONFIG)


def is_toki_pona(s: str):
    return ILO.is_toki_pona(s)
