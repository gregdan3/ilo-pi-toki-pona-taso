# STL
import random

# phase may be new, full, None
ICONS_BANNERS = [{"icon_url": "", "banner_url": "", "phase": "", "author": ""}]


def get_banner(phase: str):
    return random.choice(ICONS_BANNERS)
