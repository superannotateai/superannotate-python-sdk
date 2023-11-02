import itertools
import math
from collections import defaultdict
from typing import Any
from typing import List
from typing import Optional

from lib.core.enums import AnnotationTypes

try:
    from pydantic.v1 import BaseModel
except ImportError:
    from pydantic import BaseModel


class Annotation(BaseModel):
    instanceId: int
    type: str
    className: Optional[str]
    classId: Optional[int]
    x: Optional[Any]
    y: Optional[Any]
    points: Any
    attributes: Optional[List[Any]] = []
    keyframe: bool = False


class FrameAnnotation(BaseModel):
    frame: int
    annotations: List[Annotation] = []


class VideoFrameGenerator:
    def __init__(self, annotation_data: dict, fps: int):
        self.id_generator = iter(itertools.count(0))
        self._annotation_data = annotation_data
        duration = annotation_data["metadata"]["duration"]
        duration = 0 if not duration else duration
        self.duration = duration / (1000 * 1000)
        self.fps = fps
        self.ratio = 1000 * 1000 / fps
        self._frame_id = 1
        self.frames_count = int(math.ceil(self.duration * fps))
        self.annotations: dict = {}
        self._mapping = {}
        self._process()

    def get_frame(self, frame_no: int):
        try:
            return self.annotations[frame_no]
        except KeyError:
            self.annotations[frame_no] = FrameAnnotation(frame=frame_no)
            return self.annotations[frame_no]

    def _interpolate(
        self,
        class_name: str,
        class_id: int,
        from_frame: int,
        to_frame: int,
        data: dict,
        instance_id: int,
        steps: dict = None,
        annotation_type: str = "bbox",
    ) -> dict:
        annotations = {}
        for idx, frame_idx in enumerate(range(from_frame + 1, to_frame), 1):
            tmp_data = {}
            if annotation_type == AnnotationTypes.BBOX and data.get("points") and steps:
                tmp_data["points"] = {
                    "x1": round(data["points"]["x1"] + steps["x1"] * idx, 2),
                    "y1": round(data["points"]["y1"] + steps["y1"] * idx, 2),
                    "x2": round(data["points"]["x2"] + steps["x2"] * idx, 2),
                    "y2": round(data["points"]["y2"] + steps["y2"] * idx, 2),
                }
            elif annotation_type == AnnotationTypes.POINT:
                tmp_data = {
                    "x": round(data["x"] + steps["x"] * idx, 2),
                    "y": round(data["y"] + steps["y"] * idx, 2),
                }
            elif (
                annotation_type != AnnotationTypes.EVENT
            ):  # AnnotationTypes.POLYGON, AnnotationTypes.POLYLINE
                tmp_data["points"] = []
                for i in range(len(data["points"])):
                    tmp_data["points"].append(data["points"][i] + idx * steps[i])

            annotations[frame_idx] = Annotation(
                instanceId=instance_id,
                type=annotation_type,
                className=class_name,
                classId=class_id,
                attributes=data.get("attributes"),
                keyframe=False,
                **tmp_data
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
        if len(annotations) >= 1:
            return annotations[0]
        # Let's just leave the code for reference.
        # first_annotations = annotations[:1][0]
        # median = (
        #     first_annotations["timestamp"] // self.ratio
        # ) * self.ratio + self.ratio / 2
        # median_annotation = first_annotations
        # distance = abs(median - first_annotations["timestamp"])
        # for annotation in annotations[1:]:
        #     annotation_distance = abs(median - annotation["timestamp"])
        #     if annotation_distance < distance:
        #         distance = annotation_distance
        #         median_annotation = annotation
        # return median_annotation

    @staticmethod
    def merge_first_frame(frames_mapping):
        try:
            if 0 in frames_mapping:
                frames_mapping[0].extend(frames_mapping[1])
                frames_mapping[1] = frames_mapping[0]
                del frames_mapping[0]
        finally:
            return frames_mapping

    def _interpolate_frames(
        self,
        from_frame,
        from_frame_no,
        to_frame,
        to_frame_no,
        annotation_type,
        class_name,
        class_id,
        instance_id,
    ):
        steps = None
        frames_diff = to_frame_no - from_frame_no
        if (
            annotation_type == AnnotationTypes.BBOX
            and from_frame.get("points")
            and to_frame.get("points")
        ):
            steps = {}
            for point in "x1", "x2", "y1", "y2":
                steps[point] = round(
                    (to_frame["points"][point] - from_frame["points"][point])
                    / frames_diff,
                    2,
                )
        elif annotation_type == AnnotationTypes.POINT:
            steps = {
                "x": (to_frame["x"] - from_frame["x"]) / frames_diff,
                "y": (to_frame["y"] - from_frame["y"]) / frames_diff,
            }
        elif annotation_type in (AnnotationTypes.POLYGON, AnnotationTypes.POLYLINE):
            if len(from_frame["points"]) == len(to_frame["points"]):
                steps = [
                    (to_point - from_point) / frames_diff
                    for from_point, to_point in zip(
                        from_frame["points"], to_frame["points"]
                    )
                ]
            else:
                steps = [0] * len(from_frame["points"])

        return self._interpolate(
            class_name=class_name,
            class_id=class_id,
            from_frame=from_frame_no,
            to_frame=to_frame_no,
            data=from_frame,
            instance_id=instance_id,
            steps=steps,
            annotation_type=annotation_type,
        )

    def _process(self):
        for instance in self._annotation_data["instances"]:
            instance_id = next(self.id_generator)
            annotation_type = instance["meta"]["type"]
            if annotation_type == "comment":
                continue
            class_name = instance["meta"].get("className")
            class_id = instance["meta"].get("classId", -1)
            for parameter in instance.get("parameters", []):
                frames_mapping = defaultdict(list)
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
                        interpolated_frames.update(
                            self._interpolate_frames(
                                from_frame=from_frame,
                                from_frame_no=from_frame_no,
                                to_frame=to_frame,
                                to_frame_no=to_frame_no,
                                class_name=class_name,
                                class_id=class_id,
                                annotation_type=annotation_type,
                                instance_id=instance_id,
                            )
                        )

                    start_median_frame = self.get_median(frames_mapping[from_frame_no])
                    end_median_frame = self.get_median(frames_mapping[to_frame_no])
                    for frame_no, frame in (
                        (from_frame_no, start_median_frame),
                        (last_frame_no, end_median_frame),
                    ):
                        interpolated_frames[frame_no] = Annotation(
                            instanceId=instance_id,
                            type=annotation_type,
                            className=class_name,
                            classId=class_id,
                            x=frame.get("x"),
                            y=frame.get("y"),
                            points=frame.get("points"),
                            attributes=frame.get("attributes"),
                            keyframe=True,
                        )
                if frames_mapping and not interpolated_frames:
                    key = set(frames_mapping.keys()).pop()
                    median = self.get_median(frames_mapping[key])

                    interpolated_frames[key] = Annotation(
                        instanceId=instance_id,
                        type=annotation_type,
                        className=class_name,
                        classId=class_id,
                        x=median.get("x"),
                        y=median.get("y"),
                        points=median.get("points"),
                        attributes=median["attributes"],
                        keyframe=True,
                    )

                for frame_no, annotation in interpolated_frames.items():
                    self._add_annotation(frame_no, annotation)

    def __iter__(self):
        for frame_no in range(1, int(self.frames_count) + 1):
            frame = self.get_frame(frame_no)
            yield {**frame.dict(exclude_unset=True), **frame.dict(exclude_none=True)}
