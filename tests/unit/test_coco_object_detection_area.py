from types import SimpleNamespace

from src.superannotate.lib.app.input_converters.converters.coco_converters.sa_vector_to_coco import (  # noqa: E501
    sa_vector_to_coco_object_detection,
)


def test_object_detection_area_is_width_times_height():
    """COCO bbox `area` must be width * height.

    Regression for an operator-precedence bug: `area` was computed as
    `(x2 - x1) * y2 - y1`, i.e. `((x2 - x1) * y2) - y1`, instead of
    `(x2 - x1) * (y2 - y1)`. For the box below (from the repo's own export
    golden fixture) the old expression yields 9682 while the correct area is 437.
    """
    captured = {}

    def make_annotation(category_id, image_id, bbox, segmentation, area, anno_id):
        captured["bbox"] = bbox
        captured["area"] = area
        return {"id": anno_id, "bbox": bbox, "area": area}

    image_commons = SimpleNamespace(image_info={"id": 1})
    instances = [
        {
            "type": "bbox",
            "classId": 5,
            "points": {"x1": 437.16, "y1": 341.5, "x2": 465.23, "y2": 357.09},
        }
    ]

    _, annotations = sa_vector_to_coco_object_detection(
        make_annotation, image_commons, instances, iter([1])
    )

    assert len(annotations) == 1
    width, height = captured["bbox"][2], captured["bbox"][3]
    assert captured["area"] == int(width * height)
    assert captured["area"] == 437  # not the buggy 9682
