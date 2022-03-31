import itertools
import math
from collections import defaultdict
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel


class Annotation(BaseModel):
    instanceId: int
    type: str
    className: str
    points: Optional[Dict]
    attributes: Optional[List[Any]] = []
    keyframe: bool = False


class FrameAnnotation(BaseModel):
    frame: int
    annotations: List[Annotation] = []


class VideoFrameGenerator:
    def __init__(self, annotation_data: dict, fps: int):
        self.id_generator = iter(itertools.count(0))
        self._annotation_data = annotation_data
        self.duration = annotation_data["metadata"]["duration"] / (1000 * 1000)
        self.fps = fps
        self.ratio = 1000 * 1000 / fps
        self._frame_id = 1
        self.frames_count = int(self.duration * fps)
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
            instance_id: int,
            steps: dict = None,
            annotation_type: str = "bbox",
    ) -> dict:
        annotations = {}
        for idx, frame_idx in enumerate(range(from_frame + 1, to_frame), 1):
            points = None
            if annotation_type == "bbox" and data.get("points") and steps:
                points = {
                    "x1": round(data["points"]["x1"] + steps["x1"] * idx, 2),
                    "y1": round(data["points"]["y1"] + steps["y1"] * idx, 2),
                    "x2": round(data["points"]["x2"] + steps["x2"] * idx, 2),
                    "y2": round(data["points"]["y2"] + steps["y2"] * idx, 2),
                }
            annotations[frame_idx] = Annotation(
                instanceId=instance_id,
                type=annotation_type,
                className=class_name,
                points=points,
                attributes=data["attributes"],
                keyframe=False,
            )
        return annotations

    def _add_annotation(self, frame_no: int, annotation: Annotation):

        frame = self.get_frame(frame_no)
        frame.annotations.append(annotation)

    @staticmethod
    def pairwise(data: list):
        a, b = itertools.tee(data)
        next(b, None)
        return zip(a, b)

    def get_median(self, annotations: List[dict]) -> dict:
        if len(annotations) == 1:
            return annotations[0]
        first_annotations = annotations[:1][0]
        median = (first_annotations["timestamp"] // self.ratio) + (self.ratio / 2)
        median_annotation = first_annotations
        distance = abs(median - first_annotations["timestamp"])
        for annotation in annotations[1:]:
            annotation_distance = abs(median - annotation["timestamp"])
            if annotation_distance < distance:
                distance = annotation_distance
                median_annotation = annotation
        return median_annotation

    @staticmethod
    def merge_first_frame(frames_mapping):
        try:
            if 0 in frames_mapping:
                frames_mapping[0].extend(frames_mapping[1])
                frames_mapping[1] = frames_mapping[0]
                del frames_mapping[0]
        finally:
            return frames_mapping

    def _process(self):
        for instance in self._annotation_data["instances"]:
            instance_id = next(self.id_generator)
            annotation_type = instance["meta"]["type"]
            class_name = instance["meta"]["className"]
            for parameter in instance["parameters"]:
                frames_mapping = defaultdict(list)
                last_frame_no = None
                last_annotation = None
                interpolated_frames = {}
                for timestamp in parameter["timestamps"]:
                    frames_mapping[
                        int(math.ceil(timestamp["timestamp"] / self.ratio))
                    ].append(timestamp)
                frames_mapping = self.merge_first_frame(frames_mapping)
                for from_frame_no, to_frame_no in self.pairwise(sorted(frames_mapping)):
                    last_frame_no = to_frame_no
                    from_frame, to_frame = (
                        frames_mapping[from_frame_no][-1],
                        frames_mapping[to_frame_no][0],
                    )
                    frames_diff = to_frame_no - from_frame_no
                    if frames_diff > 1:
                        steps = None
                        if (
                                annotation_type == "bbox"
                                and from_frame.get("points")
                                and to_frame.get("points")
                        ):
                            steps = {
                                "y1": round(
                                    (
                                            to_frame["points"]["y1"]
                                            - from_frame["points"]["y1"]
                                    )
                                    / frames_diff,
                                    2,
                                ),
                                "x2": round(
                                    (
                                            to_frame["points"]["x2"]
                                            - from_frame["points"]["x2"]
                                    )
                                    / frames_diff,
                                    2,
                                ),
                                "x1": round(
                                    (
                                            to_frame["points"]["x1"]
                                            - from_frame["points"]["x1"]
                                    )
                                    / frames_diff,
                                    2,
                                ),
                                "y2": round(
                                    (
                                            to_frame["points"]["y2"]
                                            - from_frame["points"]["y2"]
                                    )
                                    / frames_diff,
                                    2,
                                ),
                            }
                        interpolated_frames.update(
                            self.interpolate_annotations(
                                class_name=class_name,
                                from_frame=from_frame_no,
                                to_frame=to_frame_no,
                                data=from_frame,
                                instance_id=instance_id,
                                steps=steps,
                                annotation_type=annotation_type,
                            )
                        )
                    start_median_frame = self.get_median(frames_mapping[from_frame_no])
                    end_median_frame = self.get_median(frames_mapping[to_frame_no])
                    interpolated_frames[from_frame_no] = Annotation(
                        instanceId=instance_id,
                        type=annotation_type,
                        className=class_name,
                        points=start_median_frame.get("points"),
                        attributes=start_median_frame["attributes"],
                        keyframe=True,
                    )
                    last_annotation = Annotation(
                        instanceId=instance_id,
                        type=annotation_type,
                        className=class_name,
                        points=end_median_frame.get("points"),
                        attributes=end_median_frame["attributes"],
                        keyframe=True,
                    )
                self._add_annotation(last_frame_no, last_annotation)
                [
                    self._add_annotation(frame_no, annotation)
                    for frame_no, annotation in interpolated_frames.items()
                ]

    def __iter__(self):
        for frame_no in range(1, int(self.frames_count) + 1):
            yield self.get_frame(frame_no).dict()
