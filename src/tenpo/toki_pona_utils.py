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
    MarkdownURLs,
    DiscordEmotes,
    DiscordSpecial,
    DiscordChannels,
    DiscordMentions,
)

EMOTES_RE = DiscordEmotes.pattern.pattern

CONFIG_SPOILERS = deepcopy(PrefConfig)
CONFIG_SPOILERS["preprocessors"] = [
    # ordered by discord's parse order
    Backticks,
    Spoilers,
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
ILO_SPOILERS = Ilo(**CONFIG_SPOILERS)

CONFIG_NO_SPOILERS = deepcopy(PrefConfig)
CONFIG_NO_SPOILERS["preprocessors"] = [
    Backticks,
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
ILO_NO_SPOILERS = Ilo(**CONFIG_NO_SPOILERS)


def is_toki_pona(s: str, spoilers: bool = True):
    if spoilers:
        return ILO_SPOILERS.is_toki_pona(s)
    return ILO_NO_SPOILERS.is_toki_pona(s)
