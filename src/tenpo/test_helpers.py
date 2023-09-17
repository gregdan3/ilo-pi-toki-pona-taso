# STL
from typing import Tuple, Callable, Generator

# LOCAL
from tenpo.toki_pona_utils import VERIFIER_MAP, NasinToki


def converter(
    strongest: NasinToki,
) -> Generator[Tuple[Callable[[str, float], bool], bool], None, None]:
    """
    Given a NasinToki  `strongest`, successively return each verifier function
    with its expected success.

    If a string would pass a test, it would also pass all weaker tests.
    If a strong would fail a test, it would also fail all stronger tests.
    This holds true for all ASCII compatible test methods.
    This is a test helper designed around this fact.
    """

    for e in NasinToki:
        func = VERIFIER_MAP[e]
        if e >= strongest:
            yield func, True
        else:
            yield func, False

        if e >= NasinToki.ALPHABETIC:
            # TODO: skipping non-ascii tests for now
            break


def li_pana_e_nimi(filename):
    with open(filename) as f:
        for line in f:
            yield line.strip()


def li_pana_e_nimi_tan_sitelen(filename):
    with open(filename) as f:
        for line in f:
            nimi_ale = tokenize(line)
            for nimi in nimi_ale:
                yield nimi.strip()
