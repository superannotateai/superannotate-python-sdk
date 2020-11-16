"""
Module to test coco conversion pipeline
"""
import json
import os
import numpy as np

import superannotate as sa


def _check_img_annot(init_values, final_values, ptype):
    image_annotations_ok = True
    for key in init_values.keys():
        try:
            assert init_values[key]["size"]["height"] == final_values[key][
                "size"]["height"]
            assert init_values[key]["size"]["width"] == final_values[key][
                "size"]["width"]

            for init_seg, final_seg in zip(
                init_values[key]["segments_info"],
                final_values[key]["segments_info"]
            ):
                assert init_seg["category_id"] == final_seg["category_id"]
                if ptype == "panoptic":
                    assert init_seg["bbox"] == final_seg["bbox"]
                    assert init_seg["area"] == final_seg["area"]
                elif ptype == "instances":
                    assert init_seg["category_id"] == final_seg["category_id"]
                    assert np.all(
                        np.abs(
                            np.array(init_seg["bbox"]) -
                            np.array(final_seg["bbox"]) < 3
                        )
                    )
                elif ptype == "keypoints":
                    final_bbox = np.array(final_seg["keypoints"])
                    final_bbox[final_bbox < 0] = 0
                    init_bbox = np.array(
                        [
                            v for i, v in enumerate(init_seg["keypoints"])
                            if (i + 1) % 3 != 0
                        ]
                    )
                    final_bbox = np.array(
                        [
                            v for i, v in enumerate(final_bbox)
                            if (i + 1) % 3 != 0
                        ]
                    )
                    assert np.all(init_bbox == final_bbox)
                else:
                    raise ValueError("Unknown type.")
        except Exception as e:
            image_annotations_ok = False
            break
    return image_annotations_ok


def _check_categories(initial_categories_list, final_categories_list, ptype):
    categories_ok = True
    for init, final in zip(initial_categories_list, final_categories_list):
        try:
            assert init["id"] == final["id"]
            if ptype == "keypoints":
                assert init["skeleton"] == final["skeleton"]
                assert set(init["keypoints"]) == set(final["keypoints"])
            elif ptype == "panoptic" or ptype == "instances":
                assert init["name"] == final["name"]
            else:
                raise ValueError("Unknown type")
        except Exception as e:
            categories_ok = False
            break
    return categories_ok


def _create_values(json_file, ptype):
    image_list = json_file["images"]
    annotation_list = json_file["annotations"]
    values = {}

    if ptype == 'panoptic':
        for img, annot in zip(image_list, annotation_list):
            key = img["file_name"].split("/")[-1].split(".")[0]
            if key not in values:
                values[key] = {"size": {}, "segments_info": {}}
            values[key]["size"] = {
                "height": img["height"],
                "width": img["width"]
            }

            key = annot["file_name"].split("/")[-1].split(".")[0]
            if key not in values:
                values[key] = {"size": {}, "segments_info": {}}
            values[key]["segments_info"] = annot["segments_info"]

    elif ptype == 'instances':
        cat_id_map = {}
        for img in image_list:
            key = img["file_name"].split("/")[-1].split(".")[0]
            if key not in values:
                values[key] = {"size": {}, "segments_info": []}
            values[key]["size"] = {
                "height": img["height"],
                "width": img["width"]
            }
            cat_id_map[img["id"]] = key

        for annot in annotation_list:
            key = cat_id_map[annot["image_id"]]
            values[key]["segments_info"].append(
                {
                    "segmentation": annot["segmentation"],
                    "bbox": annot["bbox"],
                    "category_id": annot["category_id"],
                    "area": annot["area"]
                }
            )
    else:
        cat_id_map = {}
        for img in image_list:
            key = img["file_name"].split("/")[-1].split(".")[0]
            if key not in values:
                values[key] = {"size": {}, "segments_info": []}

            values[key]["size"] = {
                "height": img["height"],
                "width": img["width"]
            }
            cat_id_map[img["id"]] = key

        for annot in annotation_list:
            key = cat_id_map[annot["image_id"]]
            values[key]["segments_info"].append(
                {
                    "bbox": annot["bbox"],
                    "category_id": annot["category_id"],
                    "keypoints": annot["keypoints"]
                }
            )

    return values


def pipeline_panoptic(tmpdir):
    """
    Pipeline for panoptic segmentation
    """
    INITIAL_FOLDER = "tests/converter_test/COCO/input/toSuperAnnotate/panoptic_segmentation"

    TEMP_FOLDER = tmpdir / "panoptic/coco2sa_out/"
    FINAL_FOLDER = tmpdir / "panoptic/sa2coco_out/"

    dataset_name = "panoptic_test"
    sa.import_annotation_format(
        INITIAL_FOLDER, str(TEMP_FOLDER), "COCO", dataset_name, "Pixel",
        "panoptic_segmentation"
    )

    sa.export_annotation_format(
        str(TEMP_FOLDER), str(FINAL_FOLDER), "COCO", dataset_name, "Pixel",
        "panoptic_segmentation"
    )

    initial_json = json.load(
        open(os.path.join(INITIAL_FOLDER, dataset_name + ".json"))
    )

    final_json = json.load(
        open(os.path.join(str(FINAL_FOLDER), dataset_name + "_train.json"))
    )

    ptype = "panoptic"
    init_values = _create_values(initial_json, ptype)
    final_values = _create_values(final_json, ptype)

    initial_categories_list = initial_json["categories"]
    final_categories_list = final_json["categories"]

    return _check_img_annot(init_values, final_values,
                            ptype) and _check_categories(
                                initial_categories_list, final_categories_list,
                                ptype
                            )


def pipeline_instance(tmpdir):
    """
    Pipeline for instance segmentation
    """
    INITIAL_FOLDER = "tests/converter_test/COCO/input/toSuperAnnotate/instance_segmentation"
    TEMP_FOLDER = tmpdir / "instances/coco2sa_out/"
    FINAL_FOLDER = tmpdir / "instances/sa2coco_out/"

    dataset_name = "instances_test"
    sa.import_annotation_format(
        INITIAL_FOLDER, str(TEMP_FOLDER), "COCO", dataset_name, "Vector",
        "instance_segmentation"
    )

    sa.export_annotation_format(
        str(TEMP_FOLDER), str(FINAL_FOLDER), "COCO", dataset_name, "Vector",
        "instance_segmentation"
    )

    initial_json = json.load(
        open(os.path.join(INITIAL_FOLDER, dataset_name + ".json"))
    )
    final_json = json.load(
        open(os.path.join(str(FINAL_FOLDER), dataset_name + "_train.json"))
    )

    ptype = "instances"
    init_values = _create_values(initial_json, ptype)
    final_values = _create_values(final_json, ptype)

    initial_categories_list = initial_json["categories"]
    final_categories_list = final_json["categories"]

    return _check_img_annot(init_values, final_values,
                            ptype) and _check_categories(
                                initial_categories_list, final_categories_list,
                                ptype
                            )


def pipeline_keypoint(tmpdir):
    """
    Pipeline for keypoints segmentation
    """
    INITIAL_FOLDER = "tests/converter_test/COCO/input/toSuperAnnotate/keypoint_detection"
    TEMP_FOLDER = tmpdir / "keypoints/coco2sa_out/"
    FINAL_FOLDER = tmpdir / "keypoints/sa2coco_out/"

    dataset_name = "person_keypoints_test"
    sa.import_annotation_format(
        INITIAL_FOLDER, str(TEMP_FOLDER), "COCO", dataset_name, "Vector",
        "keypoint_detection"
    )
    sa.export_annotation_format(
        str(TEMP_FOLDER), str(FINAL_FOLDER), "COCO", dataset_name, "Vector",
        "keypoint_detection"
    )

    initial_json = json.load(
        open(os.path.join(INITIAL_FOLDER, dataset_name + ".json"))
    )
    final_json = json.load(
        open(os.path.join(str(FINAL_FOLDER), dataset_name + "_train.json"))
    )

    ptype = "keypoints"
    initial_values = _create_values(initial_json, ptype)
    final_values = _create_values(final_json, ptype)

    initial_categories_list = initial_json["categories"]
    final_categories_list = final_json["categories"]

    return _check_img_annot(initial_values, final_values,
                            ptype) and _check_categories(
                                initial_categories_list, final_categories_list,
                                ptype
                            )


def test_pipeline(tmpdir):
    """
    Test all pipeline
    """
    assert pipeline_panoptic(tmpdir)
    assert pipeline_instance(tmpdir)
    # assert pipeline_keypoint(tmpdir)
