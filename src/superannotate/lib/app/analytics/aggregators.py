import copy
import json
from pathlib import Path
from typing import List
from typing import Optional
from typing import Union

import lib.core as constances
import pandas as pd
from dataclasses import dataclass
from lib.app.exceptions import AppException
from lib.core import ATTACHED_VIDEO_ANNOTATION_POSTFIX
from lib.core import PIXEL_ANNOTATION_POSTFIX
from lib.core import VECTOR_ANNOTATION_POSTFIX
from superannotate.logger import get_default_logger

logger = get_default_logger()


@dataclass
class VideoRawData:
    videoName: str = None
    folderName: str = None
    videoHeight: int = None
    videoWidth: int = None
    videoStatus: str = None
    videoUrl: str = None
    videoDuration: int = None
    videoError: str = None
    videoAnnotator: str = None
    videoQA: str = None
    # tag
    tagId: int = None
    tag: str = None
    # instance
    instanceId: int = None
    instanceStart: int = None
    instanceEnd: int = None
    type: str = None
    className: str = None
    createdAt: str = None
    creatorRole: str = None
    createdBy: str = None
    updatedAt: str = None
    updatedBy: str = None
    updatorRole: str = None
    pointLabels: str = None
    # parameter
    parameterId: int = None
    parameterStart: str = None
    parameterEnd: str = None
    timestampId: int = None
    meta: str = None
    attributeId: int = None
    attributeGroupName: str = None
    attributeName: str = None


class DataAggregator:
    def __init__(
        self,
        project_type: str,
        project_root: Union[str, Path],
        folder_names: Optional[List[Union[Path, str]]] = None,
    ):
        self.project_type = project_type
        self.project_root = Path(project_root)
        self.folder_names = folder_names
        self._annotation_suffix = None
        self.classes_path = self.project_root / "classes" / "classes.json"

    @property
    def annotation_suffix(self):
        if not self._annotation_suffix:
            if self.project_type == constances.ProjectType.VECTOR.name:
                self._annotation_suffix = VECTOR_ANNOTATION_POSTFIX
            elif self.project_type == constances.ProjectType.PIXEL.name:
                self._annotation_suffix = PIXEL_ANNOTATION_POSTFIX
            else:
                self._annotation_suffix = ATTACHED_VIDEO_ANNOTATION_POSTFIX
        return self._annotation_suffix

    def get_annotation_paths(self):
        annotations_paths = []
        if self.folder_names is None:
            for path in self.project_root.glob("*"):
                if path.is_file() and path.suffix == self.annotation_suffix:
                    annotations_paths.append(path)
                elif path.is_dir() and path.name != "classes":
                    annotations_paths.extend(
                        list(path.rglob(f"*{self.annotation_suffix}"))
                    )
        else:
            for folder_name in self.folder_names:
                annotations_paths.extend(
                    list(
                        (self.project_root / folder_name).rglob(
                            f"*{self.annotation_suffix:}"
                        )
                    )
                )

        if not annotations_paths:
            logger.warning(f"Could not find annotations in {self.project_root}.")
        return annotations_paths

    def check_classes_path(self):
        if not self.classes_path.is_file():
            raise AppException(
                f"SuperAnnotate classes file {self.classes_path} not found. Please provide correct project export root"
            )

    def aggregate_annotations_as_df(self):
        logger.info(
            f"Aggregating annotations from {self.project_root} as pandas DataFrame"
        )
        self.check_classes_path()
        annotation_paths = self.get_annotation_paths()

        if self.project_type in (
            constances.ProjectType.VECTOR.name,
            constances.ProjectType.PIXEL.name,
        ):
            return self.aggregate_image_annotations_as_df(annotation_paths)
        elif self.project_type == constances.ProjectType.VIDEO.name:
            return self.aggregate_video_annotations_as_df(annotation_paths)

    def aggregate_video_annotations_as_df(self, annotation_paths: List[str]):
        raws = []
        for annotation_path in annotation_paths:
            annotation_path = Path(annotation_path)
            annotation_data = json.load(open(annotation_path))
            raw_data = VideoRawData()
            # metadata
            raw_data.videoName = annotation_data["metadata"]["name"]
            raw_data.folderName = (
                annotation_path.parent.name
                if annotation_path.parent != self.project_root
                else None
            )
            raw_data.videoHeight = annotation_data["metadata"].get("height")
            raw_data.videoWidth = annotation_data["metadata"].get("width")
            raw_data.videoStatus = annotation_data["metadata"].get("status")
            raw_data.videoUrl = annotation_data["metadata"].get("url")
            raw_data.videoDuration = annotation_data["metadata"].get("duration")

            raw_data.videoError = annotation_data["metadata"].get("error")
            raw_data.videoAnnotator = annotation_data["metadata"].get("annotatorEmail")
            raw_data.videoQA = annotation_data["metadata"].get("qaEmail")
            # append tags
            for idx, tag in enumerate(annotation_data.get("tags", [])):
                tag_row = copy.copy(raw_data)
                tag_row.tagId = idx
                tag_row.tag = tag
                raws.append(tag_row)
            # append instances
            instances = annotation_data.get("instances", [])
            for idx, instance in enumerate(instances):
                instance_raw = copy.copy(raw_data)
                instance_raw.instanceId = int(idx)
                instance_raw.instanceStart = instance["meta"].get("start")
                instance_raw.instanceEnd = instance["meta"].get("end")
                instance_raw.type = instance["meta"].get("type")
                instance_raw.className = instance["meta"].get("className")
                instance_raw.createdAt = instance["meta"].get("createdAt")
                instance_raw.createdBy = (
                    instance["meta"].get("createdBy", {}).get("email")
                )
                instance_raw.creatorRole = (
                    instance["meta"].get("createdBy", {}).get("role")
                )
                instance_raw.updatedAt = instance["meta"].get("updatedAt")
                instance_raw.updatedBy = (
                    instance["meta"].get("updatedBy", {}).get("email")
                )
                instance_raw.updatorRole = (
                    instance["meta"].get("updatedBy", {}).get("role")
                )
                instance_raw.pointLabels = instance["meta"].get("pointLabels")
                parameters = instance.get("parameters", [])
                for parameter_id, parameter in enumerate(parameters):
                    parameter_raw = copy.copy(instance_raw)
                    parameter_raw.parameterId = parameter_id
                    parameter_raw.parameterStart = parameter.get("start")
                    parameter_raw.parameterEnd = parameter.get("end")
                    timestamps = parameter.get("timestamps", [])
                    for timestamp_id, timestamp in enumerate(timestamps):
                        timestamp_raw = copy.copy(parameter_raw)
                        timestamp_raw.timestampId = timestamp_id
                        timestamp_raw.meta = timestamp.get("points")
                        attributes = timestamp.get("attributes", [])
                        for attribute_id, attribute in enumerate(attributes):
                            attribute_raw = copy.copy(timestamp_raw)
                            attribute_raw.attributeId = attribute_id
                            attribute_raw.attributeGroupName = attribute.get(
                                "groupName"
                            )
                            attribute_raw.attributeName = attribute.get("name")
                            raws.append(attribute_raw)
                        if not attributes:
                            raws.append(timestamp_raw)
                    if not timestamps:
                        raws.append(parameter_raw)
                if not parameters:
                    raws.append(instance_raw)
            if not instances:
                raws.append(raw_data)
        return pd.DataFrame([raw.__dict__ for raw in raws], dtype=object)

    def aggregate_image_annotations_as_df(self, annotations_paths: List[str]):
        annotation_data = {
            "imageName": [],
            "imageHeight": [],
            "imageWidth": [],
            "imageStatus": [],
            "imagePinned": [],
            "instanceId": [],
            "className": [],
            "attributeGroupName": [],
            "attributeName": [],
            "type": [],
            "error": [],
            "locked": [],
            "visible": [],
            "trackingId": [],
            "probability": [],
            "pointLabels": [],
            "meta": [],
            "classColor": [],
            "groupId": [],
            "createdAt": [],
            "creatorRole": [],
            "creationType": [],
            "creatorEmail": [],
            "updatedAt": [],
            "updatorRole": [],
            "updatorEmail": [],
            "folderName": [],
            "imageAnnotator": [],
            "imageQA": [],
            "commentResolved": [],
            "tag": [],
        }

        classes_json = json.load(open(self.classes_path))
        class_name_to_color = {}
        class_group_name_to_values = {}
        for annotation_class in classes_json:
            name = annotation_class["name"]
            color = annotation_class["color"]
            class_name_to_color[name] = color
            class_group_name_to_values[name] = {}
            for attribute_group in annotation_class["attribute_groups"]:
                class_group_name_to_values[name][attribute_group["name"]] = []
                for attribute in attribute_group["attributes"]:
                    class_group_name_to_values[name][attribute_group["name"]].append(
                        attribute["name"]
                    )

        def __append_annotation(annotation_dict):
            for annotation_key in annotation_data:
                if annotation_key in annotation_dict:
                    annotation_data[annotation_key].append(
                        annotation_dict[annotation_key]
                    )
                else:
                    annotation_data[annotation_key].append(None)

        for annotation_path in annotations_paths:
            annotation_json = json.load(open(annotation_path))
            parts = annotation_path.name.split(self.annotation_suffix)
            if len(parts) != 2:
                continue
            image_name = parts[0]
            image_metadata = self.__get_image_metadata(image_name, annotation_json)
            annotation_instance_id = 0
            # include comments
            for annotation in annotation_json["comments"]:
                comment_resolved = annotation["resolved"]
                comment_meta = {
                    "x": annotation["x"],
                    "y": annotation["y"],
                    "comments": annotation["correspondence"],
                }
                annotation_dict = {
                    "type": "comment",
                    "meta": comment_meta,
                    "commentResolved": comment_resolved,
                }
                user_metadata = self.__get_user_metadata(annotation)
                annotation_dict.update(user_metadata)
                annotation_dict.update(image_metadata)
                __append_annotation(annotation_dict)
            # include tags
            for annotation in annotation_json["tags"]:
                annotation_dict = {"type": "tag", "tag": annotation}
                annotation_dict.update(image_metadata)
                __append_annotation(annotation_dict)
            for annotation in annotation_json["instances"]:
                annotation_type = annotation.get("type", "mask")
                annotation_class_name = annotation.get("className")
                if (
                    annotation_class_name is None
                    or annotation_class_name not in class_name_to_color
                ):
                    logger.warning(
                        "Annotation class %s not found in classes json. Skipping.",
                        annotation_class_name,
                    )
                    continue
                annotation_class_color = class_name_to_color[annotation_class_name]
                annotation_group_id = annotation.get("groupId")
                annotation_locked = annotation.get("locked")
                annotation_visible = annotation.get("visible")
                annotation_tracking_id = annotation.get("trackingId")
                annotation_meta = None
                if annotation_type in ["bbox", "polygon", "polyline", "cuboid"]:
                    annotation_meta = {"points": annotation["points"]}
                elif annotation_type == "point":
                    annotation_meta = {"x": annotation["x"], "y": annotation["y"]}
                elif annotation_type == "ellipse":
                    annotation_meta = {
                        "cx": annotation["cx"],
                        "cy": annotation["cy"],
                        "rx": annotation["rx"],
                        "ry": annotation["ry"],
                        "angle": annotation["angle"],
                    }
                elif annotation_type == "mask":
                    annotation_meta = {"parts": annotation["parts"]}
                elif annotation_type == "template":
                    annotation_meta = {
                        "connections": annotation["connections"],
                        "points": annotation["points"],
                    }
                annotation_error = annotation.get("error")
                annotation_probability = annotation.get("probability")
                annotation_point_labels = annotation.get("pointLabels")
                attributes = annotation.get("attributes")
                user_metadata = self.__get_user_metadata(annotation)
                folder_name = None
                if annotation_path.parent != Path(self.project_root):
                    folder_name = annotation_path.parent.name
                num_added = 0
                if not attributes:
                    annotation_dict = {
                        "imageName": image_name,
                        "instanceId": annotation_instance_id,
                        "className": annotation_class_name,
                        "type": annotation_type,
                        "locked": annotation_locked,
                        "visible": annotation_visible,
                        "trackingId": annotation_tracking_id,
                        "meta": annotation_meta,
                        "error": annotation_error,
                        "probability": annotation_probability,
                        "pointLabels": annotation_point_labels,
                        "classColor": annotation_class_color,
                        "groupId": annotation_group_id,
                        "folderName": folder_name,
                    }
                    annotation_dict.update(user_metadata)
                    annotation_dict.update(image_metadata)
                    __append_annotation(annotation_dict)
                    num_added = 1
                else:
                    for attribute in attributes:
                        attribute_group = attribute.get("groupName")
                        attribute_name = attribute.get("name")
                        if (
                            attribute_group
                            not in class_group_name_to_values[annotation_class_name]
                        ):
                            logger.warning(
                                "Annotation class group %s not in classes json. Skipping.",
                                attribute_group,
                            )
                            continue
                        if (
                            attribute_name
                            not in class_group_name_to_values[annotation_class_name][
                                attribute_group
                            ]
                        ):
                            logger.warning(
                                "Annotation class group value %s not in classes json. Skipping.",
                                attribute_name,
                            )
                            continue
                        annotation_dict = {
                            "imageName": image_name,
                            "instanceId": annotation_instance_id,
                            "className": annotation_class_name,
                            "attributeGroupName": attribute_group,
                            "attributeName": attribute_name,
                            "type": annotation_type,
                            "locked": annotation_locked,
                            "visible": annotation_visible,
                            "trackingId": annotation_tracking_id,
                            "meta": annotation_meta,
                            "error": annotation_error,
                            "probability": annotation_probability,
                            "pointLabels": annotation_point_labels,
                            "classColor": annotation_class_color,
                            "groupId": annotation_group_id,
                            "folderName": folder_name,
                        }
                        annotation_dict.update(user_metadata)
                        annotation_dict.update(image_metadata)
                        __append_annotation(annotation_dict)
                        num_added += 1

                if num_added > 0:
                    annotation_instance_id += 1

        df = pd.DataFrame(annotation_data)
        df = df.astype({"probability": float})
        return df

    @staticmethod
    def __get_image_metadata(image_name, annotations):
        image_metadata = {"imageName": image_name}

        image_metadata["imageHeight"] = annotations["metadata"].get("height")
        image_metadata["imageWidth"] = annotations["metadata"].get("width")
        image_metadata["imageStatus"] = annotations["metadata"].get("status")
        image_metadata["imagePinned"] = annotations["metadata"].get("pinned")
        image_metadata["imageAnnotator"] = annotations["metadata"].get("annotatorEmail")
        image_metadata["imageQA"] = annotations["metadata"].get("qaEmail")
        return image_metadata

    @staticmethod
    def __get_user_metadata(annotation):
        annotation_created_at = pd.to_datetime(annotation.get("createdAt"))
        annotation_created_by = annotation.get("createdBy")
        annotation_creator_email = None
        annotation_creator_role = None
        if annotation_created_by:
            annotation_creator_email = annotation_created_by.get("email")
            annotation_creator_role = annotation_created_by.get("role")
        annotation_creation_type = annotation.get("creationType")
        annotation_updated_at = pd.to_datetime(annotation.get("updatedAt"))
        annotation_updated_by = annotation.get("updatedBy")
        annotation_updator_email = None
        annotation_updator_role = None
        if annotation_updated_by:
            annotation_updator_email = annotation_updated_by.get("email")
            annotation_updator_role = annotation_updated_by.get("role")
        user_metadata = {
            "createdAt": annotation_created_at,
            "creatorRole": annotation_creator_role,
            "creatorEmail": annotation_creator_email,
            "creationType": annotation_creation_type,
            "updatedAt": annotation_updated_at,
            "updatorRole": annotation_updator_role,
            "updatorEmail": annotation_updator_email,
        }
        return user_metadata
