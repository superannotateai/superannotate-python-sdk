import io
from typing import Tuple

from lib.core.exceptions import ImageProcessingException
from PIL import Image
from PIL import ImageOps


class ImagePlugin:
    def __init__(self, image_bytes: io.BytesIO, max_resolution: int):
        self._image_bytes = image_bytes
        self._max_resolution = max_resolution
        self._image = Image.open(self._image_bytes)

    def _get_image(self):
        Image.MAX_IMAGE_PIXELS = None
        im = self._image

        im = ImageOps.exif_transpose(im)

        width, height = im.size

        resolution = width * height

        if resolution > self._max_resolution:
            raise ImageProcessingException(
                f"Image resolution {resolution} too large. Max supported for resolution is {self._max_resolution}"
            )
        return im

    def get_size(self) -> Tuple[float, float]:
        return self._image.size

    def generate_thumb(self):
        image = self._get_image()
        buffer = io.BytesIO()

        thumbnail_size = (128, 96)
        background = Image.new("RGB", thumbnail_size, "black")
        image.thumbnail(thumbnail_size, Image.ANTIALIAS)
        (w, h) = image.size
        background.paste(
            image, ((thumbnail_size[0] - w) // 2, (thumbnail_size[1] - h) // 2)
        )
        im = background
        im.save(buffer, "JPEG")

        buffer.seek(0)
        width, height = im.size
        return buffer, width, height

    def generate_huge(self, base_width: int = 600) -> Tuple[io.BytesIO, float, float]:
        im = self._image
        width, height = im.size
        buffer = io.BytesIO()
        h_size = int(height * base_width / width)
        im.resize((base_width, h_size), Image.ANTIALIAS).convert("RGB").save(
            buffer, "JPEG"
        )
        buffer.seek(0)
        width, height = im.size
        return buffer, width, height

    def generate_low_resolution(self, quality: int = 60, subsampling: int = -1):
        im = self._image
        buffer = io.BytesIO()
        bg = Image.new("RGBA", im.size, (255, 255, 255))
        im = im.convert("RGBA")
        bg.paste(im, mask=im)
        bg = bg.convert("RGB")
        bg.save(buffer, "JPEG", quality=quality, subsampling=subsampling)
        buffer.seek(0)
        width, height = im.size
        return buffer, width, height
