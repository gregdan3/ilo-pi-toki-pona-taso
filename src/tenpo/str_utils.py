# STL
import re
from typing import List, Tuple
from datetime import datetime

# PDM
from discord import Guild, Thread, CategoryChannel

# LOCAL
from tenpo.db import DEFAULT_REACTS, Lawa, Pali, IjoSiko, IjoPiLawaKen
from tenpo.types import (
    DiscordUser,
    DiscordActor,
    DiscordContainer,
    MessageableGuildChannel,
)
from tenpo.log_utils import getLogger
from tenpo.toki_pona_utils import EMOTES_RE

LOG = getLogger()

CONTAINER_MAP = {
    IjoSiko.ALL: "ale",
    IjoSiko.GUILD: "ma",
    IjoSiko.CATEGORY: "kulupu tomo",
    IjoSiko.CHANNEL: "tomo",
    IjoSiko.THREAD: "tomo lili",
    IjoSiko.USER: "jan",
}

PALI_MAP = {Pali.PANA: "pana", Pali.ANTE: "ante", Pali.WEKA: "weka"}
TIME_FMT = "<t:%s:%s>"
ROLE_FMT = "<@&%s>"
CHANNEL_FMT = "<#%s>"


TIMING_MAP = {
    "ale": "mi lukin lon tenpo ale",
    "ala": "mi lukin ala e toki",
    "mun": "mi lukin lon ni: mun suli li pimeja ale li suno ale",
    "wile": "mi lukin lon tenpo wile tan ilo `/lawa_ma tenpo`",
}

BANNED_REACTS = [
    "⭐",
    "<:report_this_post_to_mods:761630970544783390>",
    "<:report:988165468009406505>",
    "<:report:1128327953768521829>",
    "<:report_this_post_to_mods:987869324259754064>",
    "<:report:1162798333002264586>",
]


def get_verb(action: Pali) -> str:
    if action == Pali.PANA:
        return "pana"
    if action == Pali.ANTE:
        return "ante"
    if action == Pali.WEKA:
        return "weka"


def get_noun(item: DiscordContainer | DiscordActor) -> str:
    if isinstance(item, Guild):
        return "ma"
    if isinstance(item, CategoryChannel):
        return "kulupu tomo"
    if isinstance(item, MessageableGuildChannel):
        return "tomo"
    if isinstance(item, Thread):
        return "tomo lili"
    # if isinstance(item, DiscordUser):
    #     return "jan"
    return "ijo"


def timestamp(t: datetime):
    return int(t.timestamp())


def format_timestamp(t: datetime | int, fmt: str = "F") -> str:
    if isinstance(t, datetime):
        t = timestamp(t)
    return TIME_FMT % (t, fmt)


def format_date_ranges(ranges: List[Tuple[datetime, datetime]]) -> str:
    resp = ""
    for start, end in ranges:
        resp += format_timestamp(start) + " " + format_timestamp(end) + "\n"
    return resp


def format_cron_data(cron: str, timezone: str, length: str):
    resp = f"nasin tenpo `{timezone}` la mi open lon tenpo `{cron}` li awen lon tenpo `{length}`"
    return resp


def format_timing_data(timing: str):
    return f"{timing} la {TIMING_MAP[timing]}."


def get_discord_reacts(s: str) -> list[str]:
    return re.findall(EMOTES_RE, s)


def chunk_response(s: str, size: int = 1900) -> List[str]:
    """Split string into `size` large parts
    By default, size is `1900` to avoid Discord's limit of 2000"""
    return [s[i : i + size] for i in range(0, len(s), size)]


def codeblock_wrap(s: str) -> str:
    return f"""```
{s}
```"""


def code_wrap(s: str) -> str:
    return f"`{s}`"


def format_reacts(reacts: list[str], per_line: int = 8) -> str:
    formatted_reacts = ""
    for i, react in enumerate(reacts):
        formatted_reacts += react
        if (i + 1) % per_line == 0:
            formatted_reacts += "\n"
        else:
            formatted_reacts += " "

    return formatted_reacts.rstrip()


def format_opens_user(opens: list[str]) -> str:
    info = "open pi toki sina li ni la mi lukin ala: \n"
    f_opens = [code_wrap(open) for open in opens]  # TODO: is codeblock fine?
    f_opens = ", ".join(opens)
    return info + f_opens


def format_role_info(role_id: int):
    info = "mi lukin taso e jan pi poki ni: __%s__" % (ROLE_FMT % role_id)
    return info


def format_removed_role_info(role_id: int):
    info = "mi weka e poki ni: __%s__\nni la mi lukin e ale" % (ROLE_FMT % role_id)
    return info


def format_channel(id: int):
    """categories are channels according to pycord and they use the same escape"""
    return CHANNEL_FMT % id


def format_guild(id: int):
    # NOTE: i hope they add something better than this
    return f"<https://discord.com/channels/{id}>"


def format_rules(rules: Lawa, prefix: str):
    rules_str = prefix + ": \n"
    for ijo in IjoPiLawaKen:
        if not rules.get(ijo):
            continue

        rules_str += "  " + CONTAINER_MAP[ijo] + "\n"
        formatter = format_channel
        if ijo == IjoSiko.GUILD:
            formatter = format_guild

        for rule in rules[ijo]:
            rules_str += "    " + formatter(rule) + "\n"

    return rules_str


def format_rules_exceptions(rules: Lawa, exceptions: Lawa):
    resp = ""
    if rules[IjoSiko.ALL]:
        resp += "lawa sina la mi lukin e toki sina **lon ale**.\n"
    _ = rules.pop(IjoSiko.ALL)

    if any([rule for rule in rules.values()]):
        frules = format_rules(rules, "ni o toki pona taso")
        resp += frules
        resp += "\n"
    if any([exc for exc in exceptions.values()]):
        fexcepts = format_rules(exceptions, "ni li ken toki ale")
        resp += fexcepts
    return resp


def format_response(response: str, reacts: List[str]):
    formatted_reacts = format_reacts(reacts)
    message = "sina toki pona ala la mi pana e sitelen ni:\n%s" % formatted_reacts
    if not reacts:
        message += "\n" + "sina wile pana e sitelen sina la o kepeken `/lawa sitelen`"
    return message


def format_reacts_management(
    all_reacts: list[str],
    broken_reacts: list[str],
    banned_reacts: list[str],
) -> str:
    resp = ""
    if all_reacts:
        formatted_reacts = format_reacts(all_reacts)
        resp += (
            "sina toki pona ala la mi pana e sitelen tan kulupu ni:\n%s"
            % formatted_reacts
        )
    if broken_reacts:
        formatted_reacts = format_reacts(broken_reacts)
        resp += (
            "\n\nmi lon ala ma pi sitelen ni la mi ken ala pana e ona:\n%s"
            % formatted_reacts
        )
    if banned_reacts:
        formatted_reacts = format_reacts(banned_reacts)
        resp += (
            "\n\nsina ken ala pana e sitelen ni la mi weka e ona: \n%s"
            % formatted_reacts
        )
    if not all_reacts:
        resp += "\n\nmi jo ala e sitelen pona tan sina la sitelen sina li ante ala."
    return resp


def prep_msg_for_resend(content: str, author: int) -> str:
    # blockquote their message
    content = re.sub("^", "> ", content, flags=re.MULTILINE)
    # escape spoilers so outer spoiler works
    content = content.replace("||", r"\|\|")
    content = f"""<@{author}> li toki e ni kepeken ala toki pona: ||
{content} ||"""
    return content
