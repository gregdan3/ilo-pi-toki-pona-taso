# LOCAL
from tenpo.phase_utils import EMOJIS_LEN, PHASE_EMOJIS, PHASE_LEN_DAYS


def test_lazy_phase_len_property():
    assert PHASE_LEN_DAYS == EMOJIS_LEN
    assert PHASE_EMOJIS[0] == "🌚"
    assert PHASE_EMOJIS[EMOJIS_LEN // 2] == "🌝"
    assert ...;
