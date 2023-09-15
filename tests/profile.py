from line_profiler import profile
from tenpo.toki_pona_utils import (
    _token_is_toki_pona_alphabetic_regex,
    _token_is_toki_pona_alphabetic_set,
)


@profile
def profile_set(s: str):
    return _token_is_toki_pona_alphabetic_set(s)


@profile
def profile_regex(s: str):
    return _token_is_toki_pona_alphabetic_regex(s)


STRINGS = [
    "a",
    "misikeke",
    "kijetesantakalu",
    "f",
    "brained",
    "antidisestablishmentarianism",
]


METHODS = [profile_set, profile_regex]

ITERS = 10**5


def main():
    for method in METHODS:
        for string in STRINGS:
            for _ in range(ITERS):
                method(string)


if __name__ == "__main__":
    main()
