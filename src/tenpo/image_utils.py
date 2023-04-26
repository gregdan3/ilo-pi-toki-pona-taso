# STL
import imghdr
import logging
from typing import Optional, TypedDict

# PDM
import httpx

# LOCAL
from tenpo.log_utils import getLogger

LOG = getLogger()
ALLOWED_IMG_TYPES = {"jpeg", "png", "gif"}


class ImageDict(TypedDict):
    bytes: bytes
    extension: str


def image_wrap(image: bytes, extension: str) -> ImageDict:
    return {"bytes": image, "extension": extension}


def make_filename(image: ImageDict) -> str:
    return "image." + image["extension"]


def get_extension(content) -> Optional[str]:
    return imghdr.what(None, h=content)


async def download_image(
    url: str,
    max_file_size: int = 8 * 1024 * 1024,
    allowed_img_types: set = ALLOWED_IMG_TYPES,
    timeout_s: float = 15.0,
) -> Optional[ImageDict]:
    """
    download a [jpeg, png, or gif] or given types, of size <= 8MB or given size

    respects discord's definition of an image by default"""
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s)) as client:
        response = await client.get(url)
        if not response.status_code == 200:
            return
        content = response.content

        content_length = int(response.headers.get("content-length", "0"))
        if not content_length < max_file_size:
            return

        image_type = get_extension(content)
        if image_type not in allowed_img_types:
            return
        assert image_type

        # TODO: does discord assert dimensions strongly? maybe we need to

        return image_wrap(content, image_type)
