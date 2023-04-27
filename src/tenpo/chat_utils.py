# TODO: entire module is a bit mixed between "user facing" format and "internal" format. fix it.
# STL
import re
from typing import List

# LOCAL
from tenpo.db import Action, Container
from tenpo.log_utils import getLogger
from tenpo.toki_pona_utils import EMOTES_RE

LOG = getLogger()

CONTAINER_MAP = {
    Container.CHANNEL: "tomo",
    Container.CATEGORY: "kulupu",
    Container.GUILD: "ma",
}
ACTION_MAP = {
    Action.INSERT: "pana",
    Action.UPDATE: "ante",
    Action.DELETE: "weka",
}


DEFAULT_REACTS = [
    "🌵",
    "🌲",
    "🌲",
    "🌲",
    "🌲",
    "🌲",
    "🌳",
    "🌳",
    "🌳",
    "🌳",
    "🌳",
    "🌴",
    "🌴",
    "🌴",
    "🌴",
    "🌴",
    "🌱",
    "🌱",
    "🌱",
    "🌱",
    "🌱",
    "🌿",
    "🌿",
    "🌿",
    "🌿",
    "🌿",
    "🍀",
    "🍃",
    "🍂",
    "🍁",
    "🌷",
    "🌺",
    "🌻",
    "🐝",
    "🐌",
    "🐛",
    "🐞",
    "🦋",
]


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


def format_role_info(role_name: str):
    info = "mi lukin taso e jan pi poki __%s__" % role_name
    return info


def format_channel(id: int):
    """categories are channels according to pycord and they use the same escape"""
    return f"<#{id}>"


def format_guild(id: int):
    # NOTE: i hope they add something better than this
    return f"<https://discord.com/channels/{id}>"


def format_rules(rules, prefix):
    rules_str = prefix + ": \n"
    for val in Container:
        if not rules[val]:
            continue

        rules_str += "  " + CONTAINER_MAP[val] + "\n"
        formatter = format_channel
        if val == Container.GUILD:
            formatter = format_guild

        for rule in rules[val]:
            rules_str += "    " + formatter(rule) + "\n"

    return rules_str


def format_rules_exceptions(rules: dict, exceptions: dict):
    resp = ""
    if rules:
        frules = format_rules(rules, "ni o toki pona taso")
        resp += frules
        resp += "\n"
    if exceptions:
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
