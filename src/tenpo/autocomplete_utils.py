# LOCAL
from tenpo.log_utils import getLogger

LOG = getLogger()


def is_subsequence(s: str, opt: str) -> bool:
    s_idx, opt_idx = 0, 0
    s_len, opt_len = len(s), len(opt)

    while s_idx < s_len and opt_idx < opt_len:
        if s[s_idx].lower() == opt[opt_idx].lower():
            s_idx += 1
        opt_idx += 1

    return s_idx == s_len


def fuzzy_filter(s: str, opts: list[str]) -> list[str]:
    return [opt for opt in opts if is_subsequence(s, opt)]


def startswith_filter(s: str, opts: list[str]):
    s = s.lower()
    return list(filter(lambda x: x.lower().startswith(s), opts))


def autocomplete_filter(s: str, opts: list[str]):
    return fuzzy_filter(s, opts)
