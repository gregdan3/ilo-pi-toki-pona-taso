# STL
import os
import json

# LOCAL
from tenpo.toki_pona_utils import (
    _is_tp_dictionary,
    _is_tp_strict,
    _is_tp_loose,
    _is_tp_alphabetic,
)


def discord_messages(filename: str):
    with open(filename, "r") as f:
        j = json.loads(f.read())
        messages = j["messages"]
        for msg in messages:
            c = msg["content"]
            c = c.replace("\n", " ")
            if c:
                yield c


def main():
    ROOT = "tests/corpus/"
    P = 0.9
    dict_matches = open("out/sitelen_lipu.txt", "w")
    strict_matches = open("out/sitelen_pona.txt", "w")
    loose_matches = open("out/sitelen_ken.txt", "w")
    alphabetic_matches = open("out/sitelen_sitelen.txt", "w")
    non_matches = open("out/sitelen_ike.txt", "w")

    files = os.listdir(ROOT)
    i = 0
    for file in files:
        file = ROOT + file
        print(file)
        for msg in discord_messages(file):
            if _is_tp_dictionary(msg, P):
                print(msg, file=dict_matches)
            elif _is_tp_strict(msg, P):
                print(msg, file=strict_matches)
            elif _is_tp_loose(msg, P):
                print(msg, file=loose_matches)
            elif _is_tp_alphabetic(msg, P):
                print(msg, file=alphabetic_matches)
            else:
                print(msg, file=non_matches)

        i += 1
        if i == 50:
            break

    dict_matches.close()
    strict_matches.close()
    loose_matches.close()
    alphabetic_matches.close()
    non_matches.close()


if __name__ == "__main__":
    main()
