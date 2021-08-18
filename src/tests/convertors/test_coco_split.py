import json
import os
import tempfile
from os.path import dirname
from pathlib import Path
from unittest import TestCase

import src.lib.app.superannotate as sa


class TestCocoSplit(TestCase):
    TEST_FOLDER_PATH = (
        "data_set/converter_test/COCO/input/toSuperAnnotate/instance_segmentation"
    )

    @property
    def folder_path(self):
        return Path(
            Path(os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH))
        )

    def test_coco_split(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            image_dir = self.folder_path
            coco_json = image_dir / "instances_test.json"
            out_dir = Path(tmp_dir) / "coco_split"

            sa.coco_split_dataset(
                coco_json,
                image_dir,
                out_dir,
                ["split1", "split2", "split3"],
                [50, 30, 20],
            )

            main_json = json.load(open(coco_json))
            split1_json = json.load(open(out_dir / "split1.json"))
            split2_json = json.load(open(out_dir / "split2.json"))
            split3_json = json.load(open(out_dir / "split3.json"))

            self.assertEqual(
                len(main_json["images"]),
                (
                    len(split1_json["images"])
                    + len(split2_json["images"])
                    + len(split3_json["images"])
                ),
            )
            self.assertEqual(
                len(main_json["annotations"]),
                (
                    len(split1_json["annotations"])
                    + len(split2_json["annotations"])
                    + len(split3_json["annotations"])
                ),
            )
