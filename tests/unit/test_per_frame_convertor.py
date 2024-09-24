import json
import os.path
from unittest import TestCase

from src.superannotate.lib.core.video_convertor import VideoFrameGenerator
from tests import DATA_SET_PATH


class TestConvertor(TestCase):
    ANNOTATION_PATH = os.path.join(DATA_SET_PATH, "unit", "video_annotation.json")
    CUSTOM_CASE_5_FRAME_ANNOTATION_PATH = os.path.join(
        DATA_SET_PATH, "unit", "annotation_5_frame.json"
    )
    CUSTOM_CASE_5_FRAME_EXPECTED_ANNOTATION_PATH = os.path.join(
        DATA_SET_PATH, "unit", "annotation_5_frame_expected.json"
    )
    ONE_FRAME_ANNOTATION_PATH = os.path.join(
        DATA_SET_PATH, "unit", "one_frame_video_annotation.json"
    )

    def test_polygon_polyline_convertor(self):
        with open(self.ANNOTATION_PATH, encoding="utf-8") as f:
            payload = json.load(f)
        generator = VideoFrameGenerator(payload, fps=10)
        data = list(generator)

        from collections import defaultdict

        point_frame_map = defaultdict(list)
        frame_point_map = {
            i["frame"]: j["points"] for i in data for j in i["annotations"]
        }
        for frame, points in frame_point_map.items():
            point_frame_map[tuple(points)].append(frame)

        point_frame_count_pairs = [
            (
                (
                    226.36,
                    240.15,
                    191.47,
                    456.31,
                    240.71,
                    648.53,
                    585.2,
                    808.18,
                    1342.69,
                    779.37,
                    957.41,
                    235.89,
                    596.02,
                    186.13,
                ),
                5,
            ),
            (
                (
                    226.36,
                    240.15,
                    191.47,
                    456.31,
                    437.49,
                    569.12,
                    585.2,
                    808.18,
                    906.83,
                    933.12,
                    801.66,
                    625.14,
                    957.41,
                    235.89,
                    606.13,
                    563.07,
                ),
                6,
            ),
            ((1237.61, 194.59, 953.95, 509.98, 1110.52, 232.45), 5),
            ((1237.61, 194.59, 1270.38, 587.25, 953.95, 509.98, 1110.52, 232.45), 5),
            (
                (
                    1237.61,
                    194.59,
                    1270.38,
                    587.25,
                    995.77,
                    913.51,
                    953.95,
                    509.98,
                    1234.05,
                    191.96,
                ),
                8,
            ),
        ]
        for points, frame_count in point_frame_count_pairs:
            assert len(point_frame_map.pop(points)) == frame_count
        assert all(len(frames) == 1 for frames in point_frame_map.values())

    #  TODO write tests for one frame annotation
    # def test_one_frame_annotation(self):
    #     payload = json.load(open(self.ONE_FRAME_ANNOTATION_PATH))
    #     generator = VideoFrameGenerator(payload, fps=10)
    #     data = [i for i in generator]
    #     assert data

    def test_custom_case_5_frame(self):
        payload = json.load(open(self.CUSTOM_CASE_5_FRAME_ANNOTATION_PATH))
        generator = VideoFrameGenerator(payload, fps=1)
        data = [i for i in generator]
        with open(
            self.CUSTOM_CASE_5_FRAME_EXPECTED_ANNOTATION_PATH, encoding="utf-8"
        ) as f:
            expected = json.load(f)
            assert expected == data
