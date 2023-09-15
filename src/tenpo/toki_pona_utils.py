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

VOWELS = "aeiou"
CONSONANTS = "jklmnpstw"
ALPHABET = VOWELS + CONSONANTS
ALPHABET_SET = set(ALPHABET)

TOKEN_DELIMITERS_RE = r"\s+|(?=[.?!;:])"
TOKEN_DELIMITERS_RE = re.compile(TOKEN_DELIMITERS_RE)

CONSECUTIVE_DUPLICATES_RE = r"(.)\1+"
CONSECUTIVE_DUPLICATES_RE = re.compile(CONSECUTIVE_DUPLICATES_RE)

BARS_RE = r"\|\|[^|]+\|\|"
TICKS_RE = r"`[^`]+"
SQUOTES_RE = r"'[^']+'"
DQUOTES_RE = r'"[^"]+"'
OR_SEP = r"|"
PAIRS_RE = OR_SEP.join([BARS_RE, TICKS_RE, SQUOTES_RE, DQUOTES_RE])
PAIRS_RE = re.compile(PAIRS_RE)

URLS_RE = r"https?:\/\/\S+"
URLS_RE = re.compile(URLS_RE)

EMOTES_RE = r"<a?:\w+:\d+>"
EMOTES_RE = re.compile(EMOTES_RE)

SENT_CLEANERS = [
    partial(re.sub, PAIRS_RE, " "),
    partial(re.sub, URLS_RE, " "),
    partial(re.sub, EMOTES_RE, " "),
]

STRICT_RE = (
    rf"^(?:(?:^[{VOWELS}]|[klmnps][{VOWELS}]|[jt][aeou]|[w][aei])(?:n(?![mn]))?)+$"
)
STRICT_RE = re.compile(STRICT_RE)

ASCII_RE = rf"^(?:[{CONSONANTS}]?[{VOWELS}]n?)(?:[{CONSONANTS}][{VOWELS}]n?)*|n$"
ASCII_RE = re.compile(ASCII_RE)

ALPHABET_RE = rf"^(?:[{ALPHABET}]*$)"
ALPHABET_RE = re.compile(ALPHABET_RE)

UNIDECODE_RE = r""  # TODO
UNIDECODE_RE = re.compile(UNIDECODE_RE)

COMMON_ALLOWABLES = {
    "cw",
    "yupekosi",  # breaks alphabet, Pingo excluded
    "x",  # ala
    "y",  # anu
    "kxk",  # ken ala ken
    "wxw",  # wile ala wile
}

TOKEN_FILTERS = [
    lambda s: s.isalpha(),  # is all alphabetical; removes ""
    lambda s: not (s == s.capitalize()),  # is not Capitalized; passes ALL CAPS
    lambda s: s not in COMMON_ALLOWABLES,  # TODO: filter or part of scoring?
]
TOKEN_CLEANERS = [
    # NOTE: ORDER MATTERS
    lambda s: s.lower(),  # lowercase
    partial(re.sub, CONSECUTIVE_DUPLICATES_RE, r"\1"),  # rm consecutive duplicates
]


def tokenize(s: str) -> List[str]:
    toks_punct = re.split(TOKEN_DELIMITERS_RE, s)
    return toks_punct


def filter_tokens_ascii(tokens: List[str]):
    """Filter list of tokens to only words that should be determined to be Toki Pona or not.

    According to TOKEN_FILTERS:
    - Remove non-alphabetic strings
    - Remove strings which are Capitalized, but not ALL CAPS
    - Remove strings matching any in COMMON_ALLOWABLES
    """
    for filter in TOKEN_FILTERS:
        tokens = [token for token in tokens if filter(token)]
    return tokens


def clean_sentence(s: str) -> str:
    """
    Strip consecutive duplicates, URLs, other strings not worth checking for invalidity
    NOTE: stripping consecutive duplicates interacts badly with syllabic writing systems
    """
    for cleaner in SENT_CLEANERS:
        s = cleaner(s)
    return s


def clean_token(s: str, skip_dedupe=False) -> str:
    """Transform a token to better adhere to regex matching

    According to TOKEN_CLEANERS:
    - Make string lowercase
    - Remove consecutive duplicates from string
    """
    for cleaner in TOKEN_CLEANERS:
        s = cleaner(s)
        if skip_dedupe:
            # WARNING: if TOKEN_CLEANERS has >2 items or order changes, FIXME
            return s
    return s


def is_toki_pona(s: str, p: float = 0.9, mode: str = "alphabet") -> bool:
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
    """Assert the portion of tokens p in string s adhere to Toki Pona's phonotactics, preventing wu wo ji ti nm nn"""
    return False


def _token_is_toki_pona_ascii(s: str) -> bool:
    s = clean_token(s)
    return not not re.fullmatch(ASCII_RE, s)


def _is_toki_pona_ascii(s: str, p: float) -> bool:
    """Assert the portion of tokens p in string s adhere to Toki Pona's phonotactics, allowing wu wo ji ti nm nn"""
    s = clean_sentence(s)
    tokens = tokenize(s)
    tokens = filter_tokens_ascii(tokens)
    nimi_pona = len(tokens)
    # NOTE: could get this from pre-filter tokens; would be more lenient but less accurate (double spaces produce empty strings)
    nimi_ike = 0
    for token in tokens:
        if not _token_is_toki_pona_ascii(token):
            nimi_ike += 1
    return (nimi_ike / nimi_pona) <= (1 - p) if nimi_pona > 0 else True


def _token_is_toki_pona_alphabetic_set(s: str) -> bool:
    s = clean_token(s, skip_dedupe=True)
    return set(s).issubset(ALPHABET_SET)


def _token_is_toki_pona_alphabetic_regex(s: str) -> bool:
    """
    DO NOT USE
    Slower than _token_is_toki_pona_alphabetic_set
    """
    s = clean_token(s)
    return not not re.fullmatch(ALPHABET_RE, s)


def _is_toki_pona_alphabetic(s: str, p: float) -> bool:
    """Assert the portion of tokens p in string s contain all the letters of Toki Pona's alphabet"""
    s = clean_sentence(s)
    tokens = tokenize(s)
    tokens = filter_tokens_ascii(tokens)
    nimi_pona = len(tokens)
    # NOTE: could get this from pre-filter tokens; would be more lenient but less accurate (double spaces produce empty strings)
    nimi_ike = 0
    for token in tokens:
        if not _token_is_toki_pona_alphabetic_set(token):
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
VERIFIER_MAP["alphabet"] = _is_toki_pona_alphabetic
VERIFIER_MAP["unidecode"] = _is_toki_pona_unidecode
VERIFIER_MAP["phonemic"] = _is_toki_pona_phonemic
VERIFIER_MAP["fallback"] = _is_toki_pona_fallback
