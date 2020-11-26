from pathlib import Path

import superannotate as sa
import json


def test_coco_split(tmpdir):
    image_dir = Path(
        'tests'
    ) / 'converter_test' / 'COCO' / 'input' / 'toSuperAnnotate' / 'instance_segmentation'
    coco_json = image_dir / 'instances_test.json'
    out_dir = Path(tmpdir) / "coco_split"

    sa.coco_split_dataset(
        coco_json, image_dir, out_dir, ['split1', 'split2', 'split3'],
        [50, 30, 20]
    )

    main_json = json.load(open(coco_json))
    split1_json = json.load(open(out_dir / 'split1.json'))
    split2_json = json.load(open(out_dir / 'split2.json'))
    split3_json = json.load(open(out_dir / 'split3.json'))

    assert len(main_json['images']) == (
        len(split1_json['images']) + len(split2_json['images']) +
        len(split3_json['images'])
    )
    assert len(main_json['annotations']) == (
        len(split1_json['annotations']) + len(split2_json['annotations']) +
        len(split3_json['annotations'])
    )