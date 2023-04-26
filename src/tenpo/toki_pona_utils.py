"""
Collection of verifiers for determining if a string is or is not Toki Pona.
Each function is responsible for its own pre-processing.

`_is_toki_pona_ascii` would want to strip consecutive duplicate letters so a statement such as "mi wileeeee" would match.
`_is_toki_pona_unidecode` may not want to do this, such as for syllabaries: わわ (wawa) errantly becomes わ (wa).

"""

# STL
import re
from typing import List
from functools import partial
from collections import OrderedDict

# PDM
import unidecode

# LOCAL
from tenpo.log_utils import getLogger

LOG = getLogger()


TOKEN_DELIMITERS_RE = r"\s+|(?=[.?!;:])"
CONSECUTIVE_DUPLICATES_RE = r"(.)\1+"
SPOILERS_RE = r"\|\|[^|]+\|\|"
QUOTES_RE = r'"[^"]+"' + r"|" + r"'[^']+'"
URLS_RE = r"https?:\/\/\S+"
EMOTES_RE = r"<a?:\w+:\d+>"
SENT_CLEANERS = [SPOILERS_RE, QUOTES_RE, URLS_RE, EMOTES_RE]  # TODO: partial-ify

STRICT_REGEX = r"^(?:(?:^[aeiou]|[klmnps][aeiou]|[jt][aeou]|[w][aei])(?:n(?![mn]))?)+$"
LOOSE_REGEX = r"^(?:[jklmnpstw]?[aeiou]n?)(?:[jklmnpstw][aeiou]n?)*|n$"
UNIDECODE_REGEX = r""

COMMON_ALLOWABLES = {"msa", "cw"}

TOKEN_FILTERS = [
    lambda s: s.isalpha(),  # is all alphabetical; removes ""
    lambda s: (not (s[0].isupper())) or (s.isupper()),  # not a proper noun, or all caps
    lambda s: s not in COMMON_ALLOWABLES,
]
TOKEN_CLEANERS = [
    # NOTE: ORDER MATTERS
    lambda s: s.lower(),  # lowercase
    partial(re.sub, CONSECUTIVE_DUPLICATES_RE, r"\1"),  # rm consecutive duplicates
]


def tokenize(s: str) -> list[str]:
    toks_punct = re.split(TOKEN_DELIMITERS_RE, s)
    return toks_punct


def filter_tokens(tokens: List[str]):
    for filter in TOKEN_FILTERS:
        tokens = [token for token in tokens if filter(token)]
    return tokens


def clean_message(s: str) -> str:
    """Strip consecutive duplicates, URLs, other strings not worth checking for invalidity
    NOTE: stripping consecutive duplicates interacts badly"""
    for cleaner in SENT_CLEANERS:
        s = re.sub(cleaner, " ", s)
    return s


def clean_token(s: str, unidecode_safe=False) -> str:
    for cleaner in TOKEN_CLEANERS:
        s = cleaner(s)
    return s


def is_toki_pona(s: str, p: float = 0.9, mode: str = "ascii") -> bool:
    """
    Determine if a given string is Toki Pona:
    - for the portion of words `p`
    - with the mode `mode`
    Default to "ascii" mode that allows wuwojitinmanna
    """
    return VERIFIER_MAP[mode](s, p)


def _is_toki_pona_dict(s: str, p: float) -> bool:
    """Check that a sufficient portion of words are in jasima Linku"""
    return False


def _is_toki_pona_ascii_strict(s: str, p: float) -> bool:
    """Assert string matches a strict regex, prevents wu wo ji ti nm nn"""
    return False


def _is_toki_pona_ascii(s: str, p: float) -> bool:
    """Assert string matches a loose regex, matches [(C)V(n)]CV(n) including wuwojiti"""
    s = clean_message(s)
    tokens = tokenize(s)
    tokens = filter_tokens(tokens)
    nimi_pona = len(tokens)
    # NOTE: could get this from pre-filter tokens; would be more lenient but less accurate (double spaces produce empty strings)
    nimi_ike = 0
    for token in tokens:
        token = clean_token(token)
        if token in COMMON_ALLOWABLES:
            continue
        if not re.fullmatch(LOOSE_REGEX, token):
            nimi_ike += 1
    return (nimi_ike / nimi_pona) <= (1 - p) if nimi_pona > 0 else True


def _is_toki_pona_unidecode(s: str, p: float) -> bool:
    """Unidecode a non-ascii string and assert ascii loosely"""
    return False


def _is_toki_pona_phonemic(s: str, p: float) -> bool:
    return False


def _is_toki_pona_fallback(s: str, p: float) -> bool:
    """Progressively weaker verification"""
    for mode, verifier in VERIFIER_MAP.items():
        if mode == "fallback":
            return False
        if r := verifier(s, p):
            return r
    return False  # should be redundant


VERIFIER_MAP = OrderedDict()  # ordered by strongest to weakest
VERIFIER_MAP["dict"] = _is_toki_pona_dict
VERIFIER_MAP["strict"] = _is_toki_pona_ascii_strict
VERIFIER_MAP["ascii"] = _is_toki_pona_ascii
VERIFIER_MAP["unidecode"] = _is_toki_pona_unidecode
VERIFIER_MAP["phonemic"] = _is_toki_pona_phonemic
VERIFIER_MAP["fallback"] = _is_toki_pona_fallback
