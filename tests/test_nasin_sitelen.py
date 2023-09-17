# PDM
import pytest

# LOCAL
from tenpo.test_helpers import converter
from tenpo.toki_pona_utils import NasinToki as N

P = 0.9
LARGE_CODEBLOCK = """
```
{{ if (eq .Reaction.Emoji.Name "📌") }}
  {{if eq .Channel.OwnerID .User.ID}}
    {{if .Message.Pinned}}
      {{unpinMessage .Channel.ID .Message.ID}}
    {{else}}
      {{pinMessage .Channel.ID .Message.ID}}
    {{end}}
  {{end}}
{{end}}
```
"""

ASCII_TEST_CASES = [
    ("a", N.DICTIONARY),
    ("", N.DICTIONARY),
    (" ", N.DICTIONARY),
    ("a a a", N.DICTIONARY),
    ("toki pona li pona", N.DICTIONARY),
    ("mi moku e kili", N.DICTIONARY),
    ("jan pona mi li wawa", N.DICTIONARY),
    ("sina kepeken e ilo", N.DICTIONARY),
    ("toki li pona ala", N.DICTIONARY),
    ("sina kepeken ilo", N.DICTIONARY),
    ("li pona taso", N.DICTIONARY),
    ("    sina    seme     e     mi     ?", N.DICTIONARY),
    ("A", N.DICTIONARY),
    ("TOKI PONA LI PONA", N.DICTIONARY),
    ("MI MOKU E KILI", N.DICTIONARY),
    ("JAN pona MI LI wawa", N.DICTIONARY),
    ("sina kepeken E ilo", N.DICTIONARY),
    ("AAAAAAAAAAa", N.DICTIONARY),
    ("aAAAAAAAAAa", N.DICTIONARY),  # s.lower() MUST be before deduplication
    ("Mnmnmn", N.DICTIONARY),
    ("aAAAAAA", N.DICTIONARY),
    ("B", N.DICTIONARY),
    ("b", N.PASS),
    ("W8F4XYZ, TOKI PONA!", N.DICTIONARY),
    ("mi moku. sina lukin", N.DICTIONARY),
    ("toki! ni li pona ala", N.DICTIONARY),
    ("toki,pona,li,pona", N.DICTIONARY),
    ("mi moku; sina lukin", N.DICTIONARY),
    ("toki. sike li pona ala. o anpa.", N.DICTIONARY),
    # proper name
    ("jan Alice li pona", N.DICTIONARY),
    ("jan Bob li jo e tomo tawa", N.DICTIONARY),
    ("jan Awaja en jan Alasali en jan Akesinu li pona", N.DICTIONARY),
    ("kulupu xerox li ike", N.PASS),
    ("kulupu Xerox li ike", N.DICTIONARY),
    ("ilo W8F4XYZ li toki pona", N.DICTIONARY),
    ("homestuck", N.PASS),
    ("Homestuck", N.DICTIONARY),
    ("lipu Homestuck", N.DICTIONARY),
    ("homestuck Homestuck", N.PASS),
    ("nimi M li lon ala lon toki pona?", N.DICTIONARY),
    # consecutive duplicates
    ("waawaaaa la mi moku", N.DICTIONARY),
    ("pona muuuute", N.DICTIONARY),
    # spoilers
    ("laughing kala wawa", N.PASS),
    ("||laughing|| kala wawa", N.DICTIONARY),
    ("\n||\n\nlaughing\n\n\n|| kala wawa", N.DICTIONARY),
    # quotes
    ("ona li toki e ni: 'single quotes are boring'", N.DICTIONARY),
    ('ona li toki e ni: "double quotes are cool"', N.DICTIONARY),
    ("`https://example.com` li pona tawa mi", N.DICTIONARY),
    (
        "`many words that are illegal` ni li toki pona lon",
        N.DICTIONARY,
    ),
    ("```\nhttps://example.com\n``` li pona tawa mi", N.DICTIONARY),
    (LARGE_CODEBLOCK, N.DICTIONARY),
    # emotes
    ("toki pona li pona <a:smile:123456789>", N.DICTIONARY),
    ("mi moku e kili <a:thinking:987654321>", N.DICTIONARY),
    ("jan pona mi li wawa <a:joy:123123123>", N.DICTIONARY),
    ("mi lape <a:zzz:111222333> lon tomo", N.DICTIONARY),
    ("jan li wile e ilo <a:hammer:444555666> pona", N.DICTIONARY),
    ("toki pona li pona <:smile:123456789>", N.DICTIONARY),
    ("mi moku e kili <:thinking:987654321>", N.DICTIONARY),
    ("jan pona mi li wawa <:joy:123123123>", N.DICTIONARY),
    ("mi lape <:zzz:111222333> lon tomo", N.DICTIONARY),
    ("jan li wile e ilo <:hammer:444555666> pona", N.DICTIONARY),
    # URLs
    ("lipu https://example.com li pona", N.DICTIONARY),
    ("mi lukin e lipu https://example.com", N.DICTIONARY),
    ("https://example.com/toki-pona", N.DICTIONARY),
    ("mi wile e ni: <https://example.com> li pona", N.DICTIONARY),
    ("o lukin e ni: <https://example.com/toki-pona>", N.DICTIONARY),
    # ignorables
    ("kiwen moli 42", N.DICTIONARY),
    ("2+2=5", N.DICTIONARY),
    # typoes
    ("tmo tawa mi li pona mute la mi kepeken ona lon tenpo mute", N.DICTIONARY),
    (
        "mi pakla lon nimi pi mute lili, taso ale li pona tan ni: mi toki mute",
        N.DICTIONARY,
    ),
    ("mi kama sunopatikuna", N.LOOSE),
    ("mi wuwojiti e sina", N.LOOSE),
    ("mi pakla lon nimi pi mute lili", N.ALPHABETIC),
    ("mi mtue o kama sona", N.ALPHABETIC),
    ("mi wile pana lon sptp", N.ALPHABETIC),
    ("MNMNMN", N.ALPHABETIC),
    ("toki mMmM", N.ALPHABETIC),
]

# These are expected to fail every test except PASS, which allows any string.
# However, they actually pass one or more tests, incorrectly being identified as Toki Pona.
FALSE_POSITIVES = [
    (
        "so, to atone like papa—an awesome anon (no-name) sin man—i ate an asinine lemon-limelike tomato jalapeno isotope. 'nonsense!' amen. note to Oman: take mine katana to imitate a ninja in pantomime. atomise one nuke? 'insane misuse!' same. likewise, Susan, awaken a pepino melon in a linen pipeline. (penile) emanate semen. joke: manipulate a tame toneme to elope online tonite",
        N.PASS,  # passes strict
    ),
    (
        "I wait, I sulk, as a tool I make stoops to ineptness.",
        N.PASS,
    ),  # passes alphabetic
    ("I manipulate a passe pile", N.PASS),  # passes strict even despite duplicate
    (
        "This Is A Statement In Perfect Toki Pona, I Guarantee",
        N.PASS,
    ),  # passes all due to proper name check
]


@pytest.mark.parametrize("case, strongest", ASCII_TEST_CASES)
def test_is_toki_pona_ascii(case: str, strongest: N):
    for func, expected in converter(strongest=strongest):
        assert func(case, P) == expected


@pytest.mark.xfail(reason="False positives")
@pytest.mark.parametrize("case, strongest", FALSE_POSITIVES)
def test_false_positives_ascii(case: str, strongest: N):
    for func, expected in converter(strongest=strongest):
        assert func(case, P) == expected
