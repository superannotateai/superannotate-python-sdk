import json
import tempfile

from .input_converters.conversion import convert_platform


def filter_annotation_instances(
    annotations_dir,
    annotations_platform="Web",
    include_annotation_classes_and_types=None,
    exclude_annotation_classes_and_type=None
):
    if annotations_platform == "Web":
        tmpdir = tempfile.TemporaryDirectory()
        convert_platform(annotations_dir, tmpdir, "Web")
        annotations_dir = tmpdir

    annotations = json.load(open(annotations_dir / "annotations.json"))


    compiled_include_rules = None
    if include_annotation_classes_and_types is not None:
        compiled_include_rules =[]
        for rule in 

    filtered_annotations = {}
    for image in annotations:
        for annotation in image:
            if annotation in  f

