# PDM
from line_profiler import profile

# LOCAL
from tenpo.toki_pona_utils import (
    _is_tp_loose,
    _is_tp_strict,
    _is_tp_alphabetic,
    _is_tp_dictionary,
    __token_is_tp_dict_set,
    __token_is_tp_dict_trie,
    __token_is_tp_alphabetic_set,
    __token_is_tp_alphabetic_regex,
)

P = 0.9


@profile
def profile_is_alphabetic_set(s: str):
    return __token_is_tp_alphabetic_set(s)


@profile
def profile_is_alphabetic_regex(s: str):
    return __token_is_tp_alphabetic_regex(s)


@profile
def profile_in_dictionary_set(s: str):
    return __token_is_tp_dict_set(s)


@profile
def profile_in_dictionary_trie(s: str):
    return __token_is_tp_dict_trie(s)


@profile
def profile_sent_strict(s: str):
    return _is_tp_strict(s, P)


@profile
def profile_sent_loose(s: str):
    return _is_tp_loose(s, P)


@profile
def profile_sent_alphabetic(s: str):
    return _is_tp_alphabetic(s, P)


TOKENS = [
    "a",
    "misikeke",
    "kijetesantakalu",
    "f",
    "brained",
    "antidisestablishmentarianism",
]


TOKEN_METHODS = [
    profile_is_alphabetic_set,
    profile_is_alphabetic_regex,
    profile_in_dictionary_set,
    profile_in_dictionary_trie,
]

SENTENCES = [
    "mi wile sona pona e nasin sina",
    "mi toki pingo la mi pona ala",
    "mi toki kepeken nimi Pingo la ale li pona",
    "this is a statement in perfect toki pona",
]

SENTENCE_METHODS = [
    profile_sent_strict,
    profile_sent_loose,
    profile_sent_alphabetic,
]

ITERS = 10**5


def main():
    for method in TOKEN_METHODS:
        for string in TOKENS:
            for _ in range(ITERS):
                method(string)
    for method in SENTENCE_METHODS:
        for sent in SENTENCES:
            for _ in range(ITERS):
                method(sent)


if __name__ == "__main__":
    main()
