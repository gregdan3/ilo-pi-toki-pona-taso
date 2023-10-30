# TODO: entire module is a bit mixed between "user facing" format and "internal" format. fix it.
# STL
import re
from typing import List, Tuple
from datetime import datetime

# LOCAL
from tenpo.db import DEFAULT_REACTS, Pali, IjoSiko, IjoPiLawaKen
from tenpo.log_utils import getLogger
from tenpo.toki_pona_utils import EMOTES_RE

LOG = getLogger()

CONTAINER_MAP = {
    IjoSiko.CHANNEL: "tomo",
    IjoSiko.CATEGORY: "kulupu",
    IjoSiko.GUILD: "ma",
}

PALI_MAP = {Pali.PANA: "pana", Pali.ANTE: "ante", Pali.WEKA: "weka"}
TIME_FMT = "<t:%s:%s>"
ROLE_FMT = "<@&%s>"


TIMING_MAP = {
    "ale": "mi lukin lon tenpo ale",
    "ala": "mi lukin ala",
    "mun": "mi lukin lon ni: mun suli li pimeja ale li suno ale",
    "wile": "mi lukin lon tenpo wile tan ilo `lawa_ma tenpo`",
}


def dt_to_int(t: datetime):
    return int(t.timestamp())


def dt_to_discord_dt(t: datetime, fmt: str = "F") -> str:
    return TIME_FMT % (dt_to_int(t), fmt)


def format_date_ranges(ranges: List[Tuple[datetime, datetime]]) -> str:
    resp = ""
    for start, end in ranges:
        resp += dt_to_discord_dt(start) + " " + dt_to_discord_dt(end) + "\n"
    return resp


def format_cron_data(cron: str, timezone: str, length: str):
    resp = f"nasin tenpo `{timezone}` la mi open lon tenpo `{cron}` li awen lon tenpo `{length}`"
    return resp


def format_timing_data(timing: str):
    return f"{timing} la {TIMING_MAP[timing]}."


def get_discord_reacts(s: str):
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


def format_opens(opens: list[str]) -> str:
    opens = [code_wrap(open) for open in opens]  # TODO: is codeblock fine?
    return ", ".join(opens)


def format_opens_user(opens: list[str]) -> str:
    info = "open pi toki sina li ni la mi lukin ala: \n"
    f_opens = format_opens(opens)

    return info + f_opens


def format_role_info(role_id: int):
    info = "mi lukin taso e jan pi poki ni: " + (ROLE_FMT % role_id)
    return info


def format_channel(id: int):
    """categories are channels according to pycord and they use the same escape"""
    return f"<#{id}>"


def format_guild(id: int):
    # NOTE: i hope they add something better than this
    return f"<https://discord.com/channels/{id}>"


def format_rules(rules, prefix):
    rules_str = prefix + ": \n"
    for val in IjoPiLawaKen:
        if not rules[val]:
            continue

        rules_str += "  " + CONTAINER_MAP[val] + "\n"
        formatter = format_channel
        if val == IjoSiko.GUILD:
            formatter = format_guild

        for rule in rules[val]:
            rules_str += "    " + formatter(rule) + "\n"

    return rules_str


def format_rules_exceptions(rules: dict, exceptions: dict):
    resp = ""
    if any([rule for rule in rules.values()]):
        frules = format_rules(rules, "ni o toki pona taso")
        resp += frules
        resp += "\n"
    if any([exc for exc in exceptions.values()]):
        fexcepts = format_rules(exceptions, "ni li ken toki ale")
        resp += fexcepts
    return resp


def format_reacts_rules(reacts: List[str]):
    formatted_reacts = (
        format_reacts(reacts) if reacts else format_reacts(DEFAULT_REACTS)
    )
    message = "sina toki pona ala la mi pana e sitelen ni:\n%s" % formatted_reacts
    if not reacts:
        message += "\n" + "sina wile e sitelen sina la o kepeken ilo `/lawa sitelen`"
    return message
