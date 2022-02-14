from collections import defaultdict
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel


class Annotation(BaseModel):
    type: str
    className: str
    points: Optional[Dict]
    attributes: Optional[List[Any]] = []
    keyframe: bool = False


class FrameAnnotation(BaseModel):
    frame: int
    annotations: List[Annotation] = []

    def append_annotation(self, annotation: Annotation):
        self.annotations.append(annotation)


class Annotations(BaseModel):
    __root__: List[FrameAnnotation] = []

    def append(self, value: FrameAnnotation):
        self.__root__.append(value)


class VideoFrameGenerator:
    class DefaultDict(defaultdict):
        def __missing__(self, key):
            return self.default_factory(key)

    def __init__(self, annotation_data: dict, fps: int):
        self._annotation_data = annotation_data
        self.duration = annotation_data["metadata"]["duration"] / (1000 * 1000)
        self.fps = fps
        self.ratio = 1000 * 1000 / fps
        self._frame_id = 1
        self._frames_count = self.duration * fps
        self.annotations: dict = {}
        self._mapping = {}
        self._process()

    def get_frame(self, frame_no: int):
        try:
            return self.annotations[frame_no]
        except KeyError:
            self.annotations[frame_no] = FrameAnnotation(frame=frame_no)
            return self.annotations[frame_no]

    def interpolate_annotations(
            self,
            class_name: str,
            from_frame: int,
            to_frame: int,
            data: dict,
            steps: dict = None,
            annotation_type: str = "bbox"
    ):
        for idx, frame_idx in enumerate(range(from_frame, to_frame), 1):
            keyframe = False
            if idx == from_frame or idx - 1 == to_frame:
                keyframe = True
            points = None
            if annotation_type == "bbox":
                points = {
                    "x1": round(data["points"]["x1"] + steps["x1"] * idx, 2),
                    "y1": round(data["points"]["y1"] + steps["y1"] * idx, 2),
                    "x2": round(data["points"]["x2"] + steps["x2"] * idx, 2),
                    "y2": round(data["points"]["y2"] + steps["y2"] * idx, 2),
                }
            frame = self.get_frame(frame_idx)
            frame.annotations.append(Annotation(
                type=annotation_type,
                className=class_name,
                points=points,
                attributes=data["attributes"],
                keyframe=keyframe
            ))

    def _process(self):
        for instance in self._annotation_data["instances"]:
            for parameter in instance["parameters"]:
                time_stamp_frame_map = []
                for timestamp in parameter["timestamps"]:
                    time_stamp_frame_map.append((round(timestamp["timestamp"] / self.ratio), timestamp))
                for idx, (frame_no, timestamp_data) in enumerate(time_stamp_frame_map):
                    annotation_type = instance["meta"]["type"]
                    try:
                        next_frame_no, next_timestamp = time_stamp_frame_map[idx + 1]
                        if frame_no == next_frame_no:
                            continue
                        frames_diff = next_frame_no - frame_no
                        steps = None
                        if annotation_type == "bbox":
                            if not frames_diff:
                                steps = {
                                    "y1": 0,
                                    "x2": 0,
                                    "x1": 0,
                                    "y2": 0
                                }
                            else:
                                steps = {
                                    "y1": round(
                                        (next_timestamp["points"]["y1"] - timestamp_data["points"]["y1"]) / frames_diff,
                                        2),
                                    "x2": round(
                                        (next_timestamp["points"]["x2"] - timestamp_data["points"]["x2"]) / frames_diff,
                                        2),
                                    "x1": round(
                                        (next_timestamp["points"]["x1"] - timestamp_data["points"]["x1"]) / frames_diff,
                                        2),
                                    "y2": round(
                                        (next_timestamp["points"]["y2"] - timestamp_data["points"]["y2"]) / frames_diff,
                                        2),
                                }
                        self.interpolate_annotations(
                            class_name=instance["meta"]["className"],
                            from_frame=frame_no,
                            to_frame=next_frame_no,
                            data=timestamp_data,
                            steps=steps,
                            annotation_type=annotation_type
                        )
                    except IndexError:
                        last_frame_no, last_timestamp = time_stamp_frame_map[-1]
                        end = round(parameter["end"] / self.ratio)
                        self.interpolate_annotations(
                            annotation_type=annotation_type,
                            class_name=instance["meta"]["className"],
                            from_frame=last_frame_no,
                            to_frame=end,
                            data=last_timestamp,
                            steps={"x1": 0, "y1": 0, "x2": 0, "y2": 0}
                        )

    def __iter__(self):
        for frame_no in range(1, int(self._frames_count)):
            yield self.get_frame(frame_no).dict()
