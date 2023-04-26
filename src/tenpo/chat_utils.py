# STL
from typing import List

# LOCAL
from tenpo.log_utils import getLogger

LOG = getLogger()

def chunk_response(s: str, size: int = 1900) -> List[str]:
    """Split string into `size` large parts
    By default, size is `1900` to avoid Discord's limit of 2000"""
    return [s[i : i + size] for i in range(0, len(s), size)]


def codeblock_wrap(s: str) -> str:
    return f"""```
{s}
```"""
