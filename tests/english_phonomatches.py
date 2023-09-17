"""
Not a test file; for regenerating matches
"""

# LOCAL
from tenpo.toki_pona_utils import (
    download,
    _token_is_tp_dict,
    _token_is_tp_loose,
    _token_is_tp_strict,
    _token_is_tp_alphabetic,
)

ENGLISH_WORDS_LINK = (
    "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
)
ENGLISH_WORDS_RAW = download(ENGLISH_WORDS_LINK)
# import re
# ENGLISH_WORDS = [word.strip() for word in re.split(r"\W+", ENGLISH_WORDS) if word]
ENGLISH_WORDS = [word.strip() for word in ENGLISH_WORDS_RAW.split("\r\n") if word]


def main():
    dict_matches = open("tests/nimi/nimi_lipu.txt", "w")
    strict_matches = open("tests/nimi/nimi_pona.txt", "w")
    loose_matches = open("tests/nimi/nimi_ken.txt", "w")
    alphabetic_matches = open("tests/nimi/nimi_sitelen.txt", "w")
    non_matches = open("tests/nimi/nimi_ike.txt", "w")

    for word in ENGLISH_WORDS:
        if _token_is_tp_dict(word):
            print(word, file=dict_matches)
        elif _token_is_tp_strict(word):
            print(word, file=strict_matches)
        elif _token_is_tp_loose(word):
            print(word, file=loose_matches)
        elif _token_is_tp_alphabetic(word):
            print(word, file=alphabetic_matches)
        else:
            print(word, file=non_matches)

    dict_matches.close()
    strict_matches.close()
    loose_matches.close()
    alphabetic_matches.close()
    non_matches.close()


if __name__ == "__main__":
    main()
