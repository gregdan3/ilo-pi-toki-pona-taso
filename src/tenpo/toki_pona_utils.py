"""
Collection of verifiers for determining if a string is or is not Toki Pona.
Each function is responsible for its own pre-processing.

`_is_tp_loose` and `is_tp_strict` would want to strip consecutive duplicate letters so "mi wileeeee" matches.
`_is_tp_unicode` may not want to do this, such as for syllabaries: わわ (wawa) errantly becomes わ (wa).

"""

# STL
import re
import enum
import json
import urllib.request
from typing import List, Callable
from collections import OrderedDict
from functools import partial, cache

# PDM
import unidecode
from marisa_trie import Trie

# LOCAL
from tenpo.log_utils import getLogger

SentenceCleaner = Callable[[str], str]
Tokenizer = Callable[[str], List[str]]
TokenFilter = Callable[[List[str]], List[str]]
TokenCleaner = Callable[[str], str]
TokenValidator = Callable[[str], bool]
SentenceScorer = Callable[[int, int, float], bool]


LOG = getLogger()


class NasinToki(enum.IntEnum):
    FAIL = 0
    DICTIONARY = 10
    STRICT = 20
    LOOSE = 30
    ALPHABETIC = 40
    UNICODE = 50
    PHONEMIC = 60
    FALLBACK = 90
    PASS = 100


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

STRICT_ASCII_RE = (
    rf"^((^[{VOWELS}]|[klmnps][{VOWELS}]|[jt][aeou]|[w][aei])(n(?![mn]))?)+$"
)
STRICT_ASCII_RE = re.compile(STRICT_ASCII_RE)

STRICT_ASCII_ALLOW_N_RE = (
    rf"^((^[{VOWELS}]|[klmnps][{VOWELS}]|[jt][aeou]|[w][aei])(n(?![mn]))?)+|n$"
)
STRICT_ASCII_ALLOW_N_RE = re.compile(STRICT_ASCII_ALLOW_N_RE)


LOOSE_ASCII_RE = rf"^([{CONSONANTS}]?[{VOWELS}]n?)([{CONSONANTS}][{VOWELS}]n?)*|n$"
LOOSE_ASCII_RE = re.compile(LOOSE_ASCII_RE)

ALPHABET_RE = rf"^(?:[{ALPHABET}]*$)"
ALPHABET_RE = re.compile(ALPHABET_RE)

UNIDECODE_RE = r""  # TODO
UNIDECODE_RE = re.compile(UNIDECODE_RE)

COMMON_ALLOWABLES = {
    "cw",
    "x",  # ala
    "y",  # anu
    "kxk",  # ken ala ken
    "wxw",  # wile ala wile
}

TOKEN_FILTERS = [
    lambda s: s.isalpha(),  # is all alphabetical; removes ""
    lambda s: not (s == s.capitalize()),  # Proper Names Fail; lowercase/ALL CAPS PASS
    lambda s: s not in COMMON_ALLOWABLES,  # NOTE: Counted in nimi_ale in __is_toki_pona
]
TOKEN_CLEANERS = [
    # NOTE: ORDER MATTERS
    lambda s: s.lower(),  # lowercase
    partial(re.sub, CONSECUTIVE_DUPLICATES_RE, r"\1"),  # rm consecutive duplicates
]

JASIMA_LINK = "https://linku.la/jasima/data.json"


def download(link: str) -> str:
    return urllib.request.urlopen(link).read().decode("utf8")


JASIMA = json.loads(download(JASIMA_LINK))
JASIMA = JASIMA["data"]
DICTIONARY = [
    key
    for key in JASIMA.keys()
    if int(JASIMA[key]["recognition"]["2023-09"]) > 22
    # at and below 22, words break phonotactics
    # violates my assumption that verifier methods get stronger
]
DICTIONARY_SET = set(DICTIONARY)
DICTIONARY_TRIE = Trie(DICTIONARY)


ENGLISH_WORDS_LINK = (
    "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
)
ENGLISH_WORDS = download(ENGLISH_WORDS_LINK)


def tokenize(s: str) -> List[str]:
    toks_punct = re.split(TOKEN_DELIMITERS_RE, s)
    return toks_punct


def filter_tokens_ascii(tokens: List[str]):
    """Remove tokens which should not be checked for toki-pona-ness.

    According to TOKEN_FILTERS:
    - Remove non-alphabetic tokens
    - Remove tokens which are Capitalized, but not ALL CAPS
    - Remove tokens in COMMON_ALLOWABLES
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


@cache
def clean_token(s: str, skip_dedupe=False) -> str:
    """Transform a token to better adhere to regex matching

    According to TOKEN_CLEANERS:
    - Make string lowercase
    - Remove consecutive duplicates from string
    - Remove strings matching any in COMMON_ALLOWABLES
    """
    for cleaner in TOKEN_CLEANERS:
        s = cleaner(s)
        if skip_dedupe:
            # WARNING: if TOKEN_CLEANERS has >2 items or order changes, FIXME
            return s
    return s


@cache
def score(nimi_ike: int, nimi_ale: int, p: float):
    return (nimi_ike / nimi_ale) <= (1 - p)


#############
# VERIFIERS #
#############


def __is_toki_pona(
    s: str,
    p: float,
    clean_sentence: SentenceCleaner,
    tokenize: Tokenizer,
    filter_tokens: TokenFilter,
    clean_token: TokenCleaner,
    is_valid_token: TokenValidator,
    score: SentenceScorer,
) -> bool:
    s = clean_sentence(s)
    nimi = tokenize(s)
    nimi_ale = len(nimi)
    if not nimi_ale:
        return True

    nimi = filter_tokens(nimi)
    nimi_ike = 0
    for n in nimi:
        n = clean_token(n)
        if not is_valid_token(n):
            nimi_ike += 1
    return score(nimi_ike, nimi_ale, p)


def is_toki_pona(
    s: str, p: float = 0.9, mode: NasinToki = NasinToki.ALPHABETIC
) -> bool:
    """
    Determine if a given string is Toki Pona:
    - for the portion of words `p`
    - with the mode `mode`
    Default to "alphabet" mode, counting strings made of only letters in Toki Pona's alphabet
    """
    return VERIFIER_MAP[mode](s, p)


@cache
def __token_is_tp_dict_set(s: str) -> bool:
    return s in DICTIONARY_SET


@cache
def __token_is_tp_dict_trie(s: str) -> bool:
    """Slower than _token_is_toki_pona_dict_set"""
    return s in DICTIONARY_TRIE


@cache
def _token_is_tp_dict(s: str) -> bool:
    return __token_is_tp_dict_set(s)


def _is_tp_dictionary(s: str, p: float) -> bool:
    """Check that a sufficient portion of words are in jasima Linku"""
    return __is_toki_pona(
        s=s,
        p=p,
        clean_sentence=clean_sentence,
        tokenize=tokenize,
        filter_tokens=filter_tokens_ascii,
        clean_token=clean_token,
        is_valid_token=_token_is_tp_dict,
        score=score,
    )


@cache
def _token_is_tp_strict(s: str) -> bool:
    return not not re.fullmatch(STRICT_ASCII_ALLOW_N_RE, s)


def _is_tp_strict(s: str, p: float) -> bool:
    """Assert the portion of tokens p in string s adhere to Toki Pona's phonotactics, preventing wu wo ji ti nm nn. **Allows 'n' alone.**"""

    return __is_toki_pona(
        s=s,
        p=p,
        clean_sentence=clean_sentence,
        tokenize=tokenize,
        filter_tokens=filter_tokens_ascii,
        clean_token=clean_token,
        is_valid_token=_token_is_tp_strict,
        score=score,
    )


@cache
def _token_is_tp_loose(s: str) -> bool:
    return not not re.fullmatch(LOOSE_ASCII_RE, s)


def _is_tp_loose(s: str, p: float) -> bool:
    """Assert the portion of tokens p in string s adhere to Toki Pona's phonotactics, allowing wu wo ji ti nm nn"""

    return __is_toki_pona(
        s=s,
        p=p,
        clean_sentence=clean_sentence,
        tokenize=tokenize,
        filter_tokens=filter_tokens_ascii,
        clean_token=clean_token,
        is_valid_token=_token_is_tp_loose,
        score=score,
    )


@cache
def __token_is_tp_alphabetic_set(s: str) -> bool:
    return set(s).issubset(ALPHABET_SET)


@cache
def __token_is_tp_alphabetic_regex(s: str) -> bool:
    """
    Slower than _token_is_toki_pona_alphabetic_set
    """
    return not not re.fullmatch(ALPHABET_RE, s)


@cache
def _token_is_tp_alphabetic(s: str) -> bool:
    return __token_is_tp_alphabetic_set(s)


def _is_tp_alphabetic(s: str, p: float) -> bool:
    """Assert the portion of tokens p in string s contain all the letters of Toki Pona's alphabet"""

    return __is_toki_pona(
        s=s,
        p=p,
        clean_sentence=clean_sentence,
        tokenize=tokenize,
        filter_tokens=filter_tokens_ascii,
        clean_token=partial(clean_token, skip_dedupe=True),  # saves time
        is_valid_token=_token_is_tp_alphabetic,
        score=score,
    )


def _is_tp_unicode(s: str, p: float) -> bool:
    """Unidecode a non-ascii string and assert ascii loosely"""
    return False


def _is_tp_phonemic(s: str, p: float) -> bool:
    return False


def _is_tp_fallback(s: str, p: float) -> bool:
    """Progressively weaker verification"""
    for mode in NasinToki:
        if mode == NasinToki.FALLBACK:
            return False
        verifier = VERIFIER_MAP[mode]
        if r := verifier(s, p):
            return r
    return False  # should be redundant


VERIFIER_MAP = OrderedDict()  # ordered by strongest to weakest
VERIFIER_MAP[NasinToki.FAIL] = lambda *_, **__: False
VERIFIER_MAP[NasinToki.DICTIONARY] = _is_tp_dictionary
VERIFIER_MAP[NasinToki.STRICT] = _is_tp_strict
VERIFIER_MAP[NasinToki.LOOSE] = _is_tp_loose
VERIFIER_MAP[NasinToki.ALPHABETIC] = _is_tp_alphabetic
VERIFIER_MAP[NasinToki.UNICODE] = _is_tp_unicode
VERIFIER_MAP[NasinToki.PHONEMIC] = _is_tp_phonemic
VERIFIER_MAP[NasinToki.FALLBACK] = _is_tp_fallback
VERIFIER_MAP[NasinToki.PASS] = lambda *_, **__: True
