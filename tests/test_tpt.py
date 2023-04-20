# PDM
import pytest

# LOCAL
from tenpo.toki_pona_utils import _is_toki_pona_ascii

RATIO = 0.9


@pytest.mark.parametrize(
    "test_input, expected_output",
    [
        ("a", True),
        ("a a a", True),
        ("toki pona li pona", True),
        ("mi moku e kili", True),
        ("jan pona mi li wawa", True),
        ("sina kepeken e ilo", True),
        ("toki li pona ala", True),
        ("sina kepeken ilo", True),
        ("li pona taso", True),
        # weird things
        ("    sina    seme     e     mi     ?", True),
        # capitalization; TODO: proper names override this
        ("A", True),
        ("TOKI PONA LI PONA", True),
        ("MI MOKU E KILI", True),
        ("JAN pona MI LI wawa", True),
        ("sina kepeken E ilo", True),
        ("AAAAAAAAAAa", True),
        ("aAAAAAAAAAa", True),  # s.lower() MUST be before deduplication
        # punctuation
        ("W8F4XYZ, TOKI PONA!", True),
        ("mi moku. sina lukin", True),
        ("toki! ni li pona ala", True),
        ("toki,pona,li,pona", True),
        ("mi moku; sina lukin", True),
        ("toki. sike li pona ala. o anpa.", True),
        # proper name
        ("jan Alice li pona", True),
        ("jan Bob li jo e tomo tawa", True),
        ("jan Awaja en jan Alasali en jan Akesinu li pona", True),
        ("kulupu xerox li ike", False),
        ("kulupu Xerox li ike", True),
        ("ilo W8F4XYZ li toki pona", True),
        # consecutive duplicates
        ("waawaaaa la mi moku", True),
        ("pona muuuute", True),
        # spoilers
        ("laughing kala wawa", False),
        ("||laughing|| kala wawa", True),
        # quotes
        ("ona li toki e ni: 'single quotes are boring'", True),
        ('ona li toki e ni: "double quotes are cool"', True),
        # emotes
        ("toki pona li pona <a:smile:123456789>", True),
        ("mi moku e kili <a:thinking:987654321>", True),
        ("jan pona mi li wawa <a:joy:123123123>", True),
        ("mi lape <a:zzz:111222333> lon tomo", True),
        ("jan li wile e ilo <a:hammer:444555666> pona", True),
        ("toki pona li pona <:smile:123456789>", True),
        ("mi moku e kili <:thinking:987654321>", True),
        ("jan pona mi li wawa <:joy:123123123>", True),
        ("mi lape <:zzz:111222333> lon tomo", True),
        ("jan li wile e ilo <:hammer:444555666> pona", True),
        # URLs
        ("lipu https://example.com li pona", True),
        ("mi lukin e lipu https://example.com", True),
        ("https://example.com/toki-pona", True),
        ("mi wile e ni: <https://example.com> li pona", True),
        ("o lukin e ni: <https://example.com/toki-pona>", True),
        # ignorables
        ("kiwen moli 42", True),
        # typoes
        ("tmo tawa mi li pona mute la mi kepeken ona lon tenpo mute", True),
        ("mi pakla lon nimi pi mute lili", False),
        # caught in the wild
        ("homestuck", False),
        ("Homestuck", True),
        ("lipu Homestuck", True),
        ("homestuck Homestuck", False),
    ],
)
def test_is_toki_pona_ascii(test_input, expected_output):
    assert _is_toki_pona_ascii(test_input, RATIO) == expected_output
