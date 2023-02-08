import io
import logging
from pathlib import Path
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import cv2
import ffmpeg
from lib.core.exceptions import ImageProcessingException
from PIL import Image
from PIL import ImageDraw
from PIL import ImageOps

logger = logging.getLogger("sa")


class ImagePlugin:
    def __init__(self, image_bytes: io.BytesIO, max_resolution: int = 4096):
        self._image_bytes = image_bytes
        self._image_bytes.seek(0)
        self._max_resolution = max_resolution
        self._image = Image.open(self._image_bytes).convert("RGBA")
        self._draw = None

    def save(self, *args, **kwargs):
        self._image.save(*args, **kwargs)

    @staticmethod
    def from_array(arr):
        return Image.fromarray(arr)

    @staticmethod
    def Draw(image):
        return ImageDraw.Draw(image)

    @property
    def content(self):
        return self._image

    def show(self):
        self._image.show()

    def get_empty_image(self):
        return Image.new("RGBA", self._image.size)

    def get_empty(self):
        image_bytes = io.BytesIO()
        Image.new("RGB", self._image.size).save(image_bytes, "jpeg")
        image_bytes.seek(0)
        return ImagePlugin(image_bytes=image_bytes)

    @property
    def draw(self):
        if not self._draw:
            self._draw = ImageDraw.Draw(self._image)
        return self._draw

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
        im = self._get_image()
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
        im = self._get_image()
        buffer = io.BytesIO()
        bg = Image.new("RGBA", im.size, (255, 255, 255))
        im = im.convert("RGBA")
        bg.paste(im, mask=im)
        bg = bg.convert("RGB")
        bg.save(buffer, "JPEG", quality=quality, subsampling=subsampling)
        buffer.seek(0)
        width, height = im.size
        return buffer, width, height

    def draw_bbox(self, x1, x2, y1, y2, fill_color, outline_color):
        image = self.get_empty_image()
        draw = ImageDraw.Draw(image)
        draw.rectangle(((x1, y1), (x2, y2)), fill_color, outline_color)
        self._image.convert("RGBA")
        self._image = Image.alpha_composite(self._image, image)

    def draw_polygon(self, points: List, fill_color, outline_color):
        image = self.get_empty_image()
        draw = ImageDraw.Draw(image)
        draw.polygon(points, fill_color, outline_color)
        self._image.convert("RGBA")
        self._image = Image.alpha_composite(self._image, image)

    def draw_polyline(self, points: List, fill_color, width=2):
        image = self.get_empty_image()
        draw = ImageDraw.Draw(image)
        draw.line(points, fill_color, width=width)
        self._image.convert("RGBA")
        self._image = Image.alpha_composite(self._image, image)

    def draw_point(self, x, y, fill_color, outline_color, size=2):
        image = self.get_empty_image()
        draw = ImageDraw.Draw(image)
        draw.ellipse(
            (x - size, y - size, x + size, y + size), fill_color, outline_color
        )
        self._image.convert("RGBA")
        self._image = Image.alpha_composite(self._image, image)

    def draw_ellipse(self, cx, cy, rx, ry, fill_color, outline_color, fixed=False):
        image = self.get_empty_image()
        draw = ImageDraw.Draw(image)
        if fixed:
            draw.ellipse((cx, cy, rx, ry), fill=fill_color, outline=outline_color)
        else:
            draw.ellipse(
                (cx - rx, cy - ry, cx + rx, cy + ry),
                fill=fill_color,
                outline=outline_color,
            )
        self._image.convert("RGBA")
        self._image = Image.alpha_composite(self._image, image)

    def draw_line(self, x, y, fill_color, width=1):
        image = self.get_empty_image()
        draw = ImageDraw.Draw(image)
        draw.line((x, y), fill=fill_color, width=width)
        self._image.convert("RGBA")
        self._image = Image.alpha_composite(self._image, image)


class VideoPlugin:
    @staticmethod
    def get_frames_count(video_path: str):
        video = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG)
        count = 0
        flag = True
        while flag:
            flag, _ = video.read()
            if flag:
                count += 1
            else:
                break
        return count

    @staticmethod
    def get_fps(video_path: str) -> Union[int, float]:
        video = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG)
        return video.get(cv2.CAP_PROP_FPS)

    @staticmethod
    def get_video_rotate_code(video_path, log):
        cv2_rotations = {
            90: cv2.ROTATE_90_CLOCKWISE,
            180: cv2.ROTATE_180,
            270: cv2.ROTATE_90_COUNTERCLOCKWISE,
        }
        try:
            meta_dict = ffmpeg.probe(str(video_path))
            rot = int(meta_dict["streams"][0]["tags"]["rotate"])
            if rot:
                if log:
                    logger.info(
                        "Frame rotation of %s found. Output images will be rotated accordingly.",
                        rot,
                    )
                return cv2_rotations[rot]
        except Exception as e:
            warning_str = ""
            if "ffprobe" in str(e):
                warning_str = "This could be because ffmpeg package is not installed. To install it, run: sudo apt install ffmpeg"
            if log:
                logger.warning(
                    "Couldn't read video metadata to determine rotation. %s",
                    warning_str,
                )
            return

    @staticmethod
    def frames_generator(
        video_path: str, start_time, end_time, target_fps: Optional[float], log=True
    ):
        video = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG)
        if not video.isOpened():
            raise ImageProcessingException(
                f"Couldn't open video file {str(video_path)}."
            )
        fps = video.get(cv2.CAP_PROP_FPS)
        if not target_fps:
            target_fps = fps
        if target_fps > fps:
            target_fps = fps
        ratio = fps / target_fps
        rotate_code = VideoPlugin.get_video_rotate_code(video_path, log)
        frame_no = 0
        frame_no_with_change = 1.0
        while True:
            success, frame = video.read()
            if not success:
                break
            frame_no += 1
            if round(frame_no_with_change) != frame_no:
                continue
            frame_no_with_change += ratio
            frame_time = video.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            if end_time and frame_time > end_time:
                break
            if frame_time < start_time:
                continue
            if rotate_code:
                frame = cv2.rotate(frame, rotate_code)
            yield frame

    @staticmethod
    def get_extractable_frames(
        video_path: str,
        start_time,
        end_time,
        target_fps: float,
    ):
        total = VideoPlugin.get_frames_count(video_path)
        total_with_fps = sum(
            1
            for _ in VideoPlugin.frames_generator(
                video_path, start_time, end_time, target_fps, log=False
            )
        )
        zero_fill_count = len(str(total))
        video_name = Path(video_path).stem
        frame_names = []
        for i in range(1, total_with_fps + 1):
            frame_name = f"{video_name}_{str(i).zfill(zero_fill_count)}.jpg"
            frame_names.append(frame_name)
        return frame_names

    @staticmethod
    def extract_frames(
        video_path: str,
        start_time,
        end_time,
        extract_path: str,
        limit: int,
        target_fps: float,
        chunk_size: int = 100,
    ) -> List[str]:
        total_num_of_frames = VideoPlugin.get_frames_count(video_path)
        zero_fill_count = len(str(total_num_of_frames))
        video_name = Path(video_path).stem
        extracted_frame_no = 1
        extracted_frames_paths = []
        for frame in VideoPlugin.frames_generator(
            video_path, start_time, end_time, target_fps
        ):
            if len(extracted_frames_paths) >= limit:
                break
            path = str(
                Path(extract_path)
                / (
                    video_name
                    + "_"
                    + str(extracted_frame_no).zfill(zero_fill_count)
                    + ".jpg"
                )
            )
            extracted_frame_no += 1
            cv2.imwrite(path, frame)
            extracted_frames_paths.append(path)
            if len(extracted_frames_paths) % chunk_size == 0:
                yield extracted_frames_paths
                extracted_frames_paths.clear()
        if extracted_frames_paths:
            yield extracted_frames_paths
