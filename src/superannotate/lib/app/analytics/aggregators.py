import copy
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List
from typing import Optional
from typing import Union

import lib.core as constances
import pandas as pd
from lib.app.exceptions import AppException
from lib.core import PIXEL_ANNOTATION_POSTFIX
from lib.core import VECTOR_ANNOTATION_POSTFIX

logger = logging.getLogger("sa")


@dataclass
class ImageRowData:
    itemName: str = None
    itemHeight: int = None
    itemWidth: int = None
    itemStatus: str = None
    itemPinned: bool = None
    instanceId: int = None
    className: str = None
    attributeGroupName: str = None
    attributeName: str = None
    type: str = None
    error: str = None
    locked: bool = None
    visible: bool = None
    trackingId: int = None
    probability: int = None
    pointLabels: str = None
    meta: str = None
    classColor: str = None
    groupId: int = None
    createdAt: str = None
    creatorRole: str = None
    creationType: str = None
    creatorEmail: str = None
    updatedAt: str = None
    updatorRole: str = None
    updatorEmail: str = None
    folderName: str = None
    itemAnnotator: str = None
    itemQA: str = None
    commentResolved: str = None
    tag: str = None


@dataclass
class VideoRawData:
    itemName: str = None
    folderName: str = None
    itemHeight: int = None
    itemWidth: int = None
    itemStatus: str = None
    itemURL: str = None
    itemDuration: int = None
    error: str = None
    itemAnnotator: str = None
    itemQA: str = None
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


class DocumentRawData:
    itemName: str = None
    folderName: str = None
    itemStatus: str = None
    itemURL: str = None
    itemAnnotator: str = None
    itemQA: str = None
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
    createdBy: str = None
    creatorRole: str = None
    updatedAt: str = None
    updatedBy: str = None
    updatorRole: str = None
    # attribute
    attributeId: int = None
    attributeGroupName: str = None
    attributeName: str = None


class DataAggregator:
    MAPPERS = {
        "event": lambda annotation: None,
        "bbox": lambda annotation: annotation["points"],
        "polygon": lambda annotation: annotation["points"],
        "polyline": lambda annotation: annotation["points"],
        "cuboid": lambda annotation: annotation["points"],
        "comment": lambda annotation: annotation["correspondence"],
        "point": lambda annotation: {"x": annotation["x"], "y": annotation["y"]},
        "ellipse": lambda annotation: dict(
            cx=annotation["cx"],
            cy=annotation["cy"],
            rx=annotation["rx"],
            ry=annotation["ry"],
            angle=annotation["angle"],
        ),
        "tag": lambda annotation: None,
        "mask": lambda annotation: {"parts": annotation["parts"]},
        "template": lambda annotation: None,
        "rbbox": lambda annotation: annotation["points"],
        "comment_inst": lambda annotation: annotation["points"],
    }

    def __init__(
        self,
        project_type: str,
        project_root: Union[str, Path],
        folder_names: Optional[List[Union[Path, str]]] = None,
    ):
        self.project_type = project_type
        if isinstance(project_type, str):
            self.project_type = constances.ProjectType(project_type)
        self.project_root = Path(project_root)
        self.folder_names = folder_names
        self._annotation_suffix = None
        self.classes_path = self.project_root / "classes" / "classes.json"

    def _set_annotation_suffix(self, path):

        fname = next((x for x in path.glob("*.json")), None)
        if not fname:
            self._annotation_suffix = ".json"
        elif VECTOR_ANNOTATION_POSTFIX in fname.name:
            self._annotation_suffix = VECTOR_ANNOTATION_POSTFIX
        elif PIXEL_ANNOTATION_POSTFIX in fname.name:
            self._annotation_suffix = PIXEL_ANNOTATION_POSTFIX
        else:
            self._annotation_suffix = ".json"

    def get_annotation_paths(self):
        annotations_paths = []
        if self.folder_names is None:
            self._set_annotation_suffix(self.project_root)
            for path in self.project_root.glob("*"):
                if path.is_file() and self._annotation_suffix in path.name:
                    annotations_paths.append(path)
                elif path.is_dir() and path.name != "classes":
                    annotations_paths.extend(
                        list(path.rglob(f"*{self._annotation_suffix}"))
                    )
        else:
            for folder_name in self.folder_names:
                self._set_annotation_suffix(self.project_root / folder_name)
                annotations_paths.extend(
                    list(
                        (self.project_root / folder_name).rglob(
                            f"*{self._annotation_suffix}"
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
            constances.ProjectType.VECTOR,
            constances.ProjectType.PIXEL,
        ):
            return self.aggregate_image_annotations_as_df(annotation_paths)
        elif self.project_type is constances.ProjectType.VIDEO:
            return self.aggregate_video_annotations_as_df(annotation_paths)
        elif self.project_type is constances.ProjectType.DOCUMENT:
            return self.aggregate_document_annotations_as_df(annotation_paths)
        else:
            raise AppException(
                f"The function is not supported for {self.project_type.name} projects."
            )

    def __add_attributes_to_raws(self, raws, attributes, element_raw):
        for attribute_id, attribute in enumerate(attributes):
            attribute_raw = copy.copy(element_raw)
            attribute_raw.attributeId = attribute_id
            attribute_raw.attributeGroupName = attribute.get("groupName")
            attribute_raw.attributeName = attribute.get("name")
            raws.append(attribute_raw)
        if not attributes:
            raws.append(element_raw)
        return raws

    def aggregate_video_annotations_as_df(self, annotation_paths: List[str]):
        raws = []
        for annotation_path in annotation_paths:
            annotation_path = Path(annotation_path)
            annotation_data = json.load(open(annotation_path))
            raw_data = VideoRawData()
            # metadata
            raw_data.itemName = annotation_data["metadata"]["name"]
            raw_data.folderName = (
                annotation_path.parent.name
                if annotation_path.parent != self.project_root
                else None
            )
            raw_data.itemHeight = annotation_data["metadata"].get("height")
            raw_data.itemWidth = annotation_data["metadata"].get("width")
            raw_data.itemStatus = annotation_data["metadata"].get("status")
            raw_data.itemURL = annotation_data["metadata"].get("url")
            raw_data.itemDuration = annotation_data["metadata"].get("duration")

            raw_data.error = annotation_data["metadata"].get("error")
            raw_data.itemAnnotator = annotation_data["metadata"].get("annotatorEmail")
            raw_data.itemQA = annotation_data["metadata"].get("qaEmail")
            # append tags
            for idx, tag in enumerate(annotation_data.get("tags", [])):
                tag_row = copy.copy(raw_data)
                tag_row.tagId = idx
                tag_row.tag = tag
                raws.append(tag_row)
            # append instances
            instances = annotation_data.get("instances", [])
            for idx, instance in enumerate(instances):
                instance_type = instance["meta"].get("type", "event")
                if instance_type == "comment":
                    instance_type = "comment_inst"
                instance_raw = copy.copy(raw_data)
                instance_raw.instanceId = int(idx)
                instance_raw.instanceStart = instance["meta"].get("start")
                instance_raw.instanceEnd = instance["meta"].get("end")
                instance_raw.type = instance_type
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
                if instance_raw.type == "tag":
                    attributes = instance["meta"].get("attributes", [])
                    raws = self.__add_attributes_to_raws(raws, attributes, instance_raw)
                for parameter_id, parameter in enumerate(parameters):
                    parameter_raw = copy.copy(instance_raw)
                    parameter_raw.parameterId = parameter_id
                    parameter_raw.parameterStart = parameter.get("start")
                    parameter_raw.parameterEnd = parameter.get("end")
                    timestamps = parameter.get("timestamps", [])
                    for timestamp_id, timestamp in enumerate(timestamps):
                        timestamp_raw = copy.copy(parameter_raw)
                        timestamp_raw.timestampId = timestamp_id
                        timestamp_raw.meta = self.MAPPERS[instance_type](timestamp)
                        attributes = timestamp.get("attributes", [])
                        raws = self.__add_attributes_to_raws(
                            raws, attributes, timestamp_raw
                        )
                    if not timestamps:
                        raws.append(parameter_raw)
                if not parameters and instance_type != "tag":
                    raws.append(instance_raw)
            if not instances:
                raws.append(raw_data)
        df = pd.DataFrame([raw.__dict__ for raw in raws], dtype=object)
        return df.where(pd.notnull(df), None)

    def aggregate_document_annotations_as_df(self, annotation_paths: List[str]):
        raws = []
        for annotation_path in annotation_paths:
            annotation_path = Path(annotation_path)
            annotation_data = json.load(open(annotation_path))
            raw_data = DocumentRawData()
            # metadata
            raw_data.itemName = annotation_data["metadata"]["name"]
            raw_data.folderName = (
                annotation_path.parent.name
                if annotation_path.parent != self.project_root
                else None
            )
            raw_data.itemStatus = annotation_data["metadata"].get("status")
            raw_data.itemURL = annotation_data["metadata"].get("url")
            raw_data.itemAnnotator = annotation_data["metadata"].get("annotatorEmail")
            raw_data.itemQA = annotation_data["metadata"].get("qaEmail")
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
                instance_raw.instanceStart = instance.get("start")
                instance_raw.instanceEnd = instance.get("end")
                instance_raw.type = instance.get("type")
                instance_raw.className = instance.get("className")
                instance_raw.createdAt = instance.get("createdAt")
                instance_raw.createdBy = instance.get("createdBy", {}).get("email")
                instance_raw.creatorRole = instance.get("createdBy", {}).get("role")
                instance_raw.updatedAt = instance.get("updatedAt")
                instance_raw.updatedBy = instance.get("updatedBy", {}).get("email")
                instance_raw.updatorRole = instance.get("updatedBy", {}).get("role")
                attributes = instance.get("attributes", [])
                # append attributes
                for attribute_id, attribute in enumerate(attributes):
                    attribute_raw = copy.copy(instance_raw)
                    attribute_raw.attributeId = attribute_id
                    attribute_raw.attributeGroupName = attribute.get("groupName")
                    attribute_raw.attributeName = attribute.get("name")
                    raws.append(attribute_raw)
                if not attributes:
                    raws.append(instance_raw)
            if not instances:
                raws.append(raw_data)
        df = pd.DataFrame([raw.__dict__ for raw in raws], dtype=object)
        return df.where(pd.notnull(df), None)

    def aggregate_image_annotations_as_df(self, annotations_paths: List[str]):

        classes_json = json.load(open(self.classes_path))
        class_name_to_color = {}
        class_group_name_to_values = {}
        rows = []
        freestyle_attributes = set()
        for annotation_class in classes_json:
            name = annotation_class["name"]
            color = annotation_class["color"]
            class_name_to_color[name] = color
            class_group_name_to_values[name] = {}
            for attribute_group in annotation_class["attribute_groups"]:
                group_type = attribute_group.get("group_type")
                group_id = attribute_group.get("id")
                if group_type and group_type in ["text", "numeric"]:
                    freestyle_attributes.add(group_id)
                class_group_name_to_values[name][attribute_group["name"]] = []
                for attribute in attribute_group["attributes"]:
                    class_group_name_to_values[name][attribute_group["name"]].append(
                        attribute["name"]
                    )

        for annotation_path in annotations_paths:
            row_data = ImageRowData()
            annotation_json = None
            with open(annotation_path) as fp:
                annotation_json = json.load(fp)
            parts = Path(annotation_path).name.split(self._annotation_suffix)
            row_data = self.__fill_image_metadata(row_data, annotation_json["metadata"])
            annotation_instance_id = 0

            # include comments
            for annotation in annotation_json["comments"]:
                comment_row = copy.copy(row_data)
                comment_row.comment_resolved = annotation["resolved"]
                comment_row.comment = DataAggregator.MAPPERS["comment"](annotation)
                comment_row = self.__fill_user_metadata(row_data, annotation)
                rows.append(comment_row)
            # include tags
            for idx, tag in enumerate(annotation_json["tags"]):
                tag_row = copy.copy(row_data)
                tag_row.tagId = idx
                tag_row.rag = tag
                rows.append(tag_row)

            # Instances
            for idx, annotation in enumerate(annotation_json["instances"]):
                instance_row = copy.copy(row_data)
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
                instance_row.classColor = class_name_to_color[annotation_class_name]
                instance_row.groupId = annotation.get("groupId")
                instance_row.locked = annotation.get("locked")
                instance_row.visible = annotation.get("visible")
                instance_row.trackingId = annotation.get("trackingId")
                instance_row.type = annotation.get("type")
                instance_row.meta = DataAggregator.MAPPERS[annotation_type](annotation)
                instance_row.error = annotation.get("error")
                instance_row.probability = annotation.get("probability")
                instance_row.pointLabels = annotation.get("pointLabels")
                instance_row.instanceId = idx
                attributes = annotation.get("attributes")
                instance_row = self.__fill_user_metadata(instance_row, annotation)
                folder_name = None
                if Path(annotation_path).parent != Path(self.project_root):
                    folder_name = Path(annotation_path).parent.name
                instance_row.folderName = folder_name
                num_added = 0
                if not attributes:
                    rows.append(instance_row)
                    num_added = 1
                else:
                    for attribute in attributes:
                        attribute_row = copy.copy(instance_row)
                        attribute_group = attribute.get("groupName")
                        group_id = attribute.get("groupId")
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
                            and group_id not in freestyle_attributes
                        ):
                            logger.warning(
                                f"Annotation class group value {attribute_name} not in classes json. Skipping."
                            )
                            continue

                        else:
                            attribute_row.attributeGroupName = attribute_group
                            attribute_row.attributeName = attribute_name

                        rows.append(attribute_row)
                        num_added += 1

                if num_added > 0:
                    annotation_instance_id += 1

        df = pd.DataFrame([row.__dict__ for row in rows], dtype=object)
        df = df.astype({"probability": float})
        return df

    @staticmethod
    def __fill_image_metadata(raw_data, metadata):
        raw_data.itemName = metadata.get("name")
        raw_data.itemHeight = metadata.get("height")
        raw_data.itemWidth = metadata.get("width")
        raw_data.itemStatus = metadata.get("status")
        raw_data.itemPinned = metadata.get("pinned")
        raw_data.itemAnnotator = metadata.get("annotatorEmail")
        raw_data.itemQA = metadata.get("qaEmail")
        return raw_data

    @staticmethod
    def __fill_user_metadata(row_data, annotation):
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
        row_data.createdAt = annotation_created_at
        row_data.creatorRole = annotation_creator_role
        row_data.creatorEmail = annotation_creator_email
        row_data.creationType = annotation_creation_type
        row_data.updatedAt = annotation_updated_at
        row_data.updatorRole = annotation_updator_role
        row_data.updatorEmail = annotation_updator_email
        return row_data
