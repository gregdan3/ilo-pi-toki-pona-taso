# PDM
import pytest

# LOCAL
from tenpo.test_helpers import li_pana_e_nimi, li_pana_e_nimi_tan_sitelen
from tenpo.toki_pona_utils import (
    DICTIONARY,
    tokenize,
    _token_is_tp_dict,
    _token_is_tp_loose,
    _token_is_tp_strict,
    _token_is_tp_alphabetic,
)


@pytest.mark.parametrize("nimi", DICTIONARY)
def test_dict(nimi: str):
    assert _token_is_tp_dict(nimi)
    assert _token_is_tp_strict(nimi)
    assert _token_is_tp_loose(nimi)
    assert _token_is_tp_alphabetic(nimi)


@pytest.mark.parametrize(
    "nimi",
    [nimi for nimi in li_pana_e_nimi("tests/nimi/nimi_lipu.txt")]
    + [
        tokenize(sitelen)
        for sitelen in li_pana_e_nimi_tan_sitelen("tests/sitelen/sitelen_lipu.txt")
    ],
)
def test_lipu(nimi):
    assert _token_is_tp_dict(nimi)
    assert _token_is_tp_strict(nimi)
    assert _token_is_tp_loose(nimi)
    assert _token_is_tp_alphabetic(nimi)


@pytest.mark.parametrize(
    "nimi",
    [nimi for nimi in li_pana_e_nimi("tests/nimi/nimi_pona.txt")]
    + [
        tokenize(sitelen)
        for sitelen in li_pana_e_nimi_tan_sitelen("tests/sitelen/sitelen_pona.txt")
    ],
)
def test_pona(nimi: str):
    assert not _token_is_tp_dict(nimi)
    assert _token_is_tp_strict(nimi)
    assert _token_is_tp_loose(nimi)
    assert _token_is_tp_alphabetic(nimi)


@pytest.mark.parametrize(
    "nimi",
    [nimi for nimi in li_pana_e_nimi("tests/nimi/nimi_ken.txt")]
    + [
        tokenize(sitelen)
        for sitelen in li_pana_e_nimi_tan_sitelen("tests/sitelen/sitelen_ken.txt")
    ],
)
def test_ken(nimi: str):
    assert not _token_is_tp_dict(nimi)
    assert not _token_is_tp_strict(nimi)
    assert _token_is_tp_loose(nimi)
    assert _token_is_tp_alphabetic(nimi)


# @pytest.mark.slow(reason="17k")
# @pytest.mark.parametrize(
#     "nimi",
#     [nimi for nimi in li_pana_e_nimi("tests/nimi/nimi_sitelen.txt")]
#     + [
#         tokenize(nimi) for nimi in li_pana_e_nimi_tan_sitelen("tests/sitelen/sitelen_sitelen.txt")
#     ],
# )
# def test_sitelen(nimi: str):
#     assert not _token_is_tp_dict(nimi)
#     assert not _token_is_tp_strict(nimi)
#     assert not _token_is_tp_loose(nimi)
#     assert _token_is_tp_alphabetic(nimi)
#
#
# @pytest.mark.slow(reason="350k")
# @pytest.mark.parametrize(
#     "nimi",
#     [nimi for nimi in li_pana_e_nimi("tests/nimi/nimi_ike.txt")]
#     + [tokenize(nimi) for nimi in li_pana_e_nimi_tan_sitelen("tests/sitelen/sitelen_ike.txt")],
# )
# def test_ike(nimi: str):
#     assert not _token_is_tp_dict(nimi)
#     assert not _token_is_tp_strict(nimi)
#     assert not _token_is_tp_loose(nimi)
#     assert not _token_is_tp_alphabetic(nimi)
