import json
import logging
import os
import sys
import time
from pathlib import Path

from PIL import Image

logger = logging.getLogger("superannotate-python-sdk")


class YOLOConverter():
    def __init__(self, args):
        logger.warning(
            "Beta feature. YOLO to SuperAnnotate annotation format converter is in BETA state."
        )
        self.dataset_name = args.dataset_name
        self.project_type = args.project_type
        self.task = args.task
        self.output_dir = args.output_dir
        self.export_root = args.export_root
        self.direction = args.direction
        self.platform = args.platform

    def save_desktop_format(self, classes, files_dict):
        path = Path(self.output_dir)
        cat_id_map = {}
        new_classes = []
        for idx, class_ in enumerate(classes):
            cat_id_map[class_['name']] = idx + 2
            class_['id'] = idx + 2
            new_classes.append(class_)
        with open(path.joinpath('classes.json'), 'w') as fw:
            json.dump(new_classes, fw)

        meta = {
            "type": "meta",
            "name": "lastAction",
            "timestamp": int(round(time.time() * 1000))
        }
        new_json = {}
        files_path = []
        (path / 'images' / 'thumb').mkdir()
        for file_name, json_data in files_dict.items():
            file_name = file_name.replace('___objects.json', '')
            if not (path / 'images' / file_name).exists():
                continue

            for js_data in json_data:
                if 'className' in js_data:
                    js_data['classId'] = cat_id_map[js_data['className']]
            json_data.append(meta)
            new_json[file_name] = json_data

            files_path.append(
                {
                    'srcPath':
                        str(path.resolve() / file_name),
                    'name':
                        file_name,
                    'imagePath':
                        str(path.resolve() / file_name),
                    'thumbPath':
                        str(
                            path.resolve() / 'images' / 'thumb' /
                            ('thmb_' + file_name + '.jpg')
                        ),
                    'valid':
                        True
                }
            )

            img = Image.open(path / 'images' / file_name)
            img.thumbnail((168, 120), Image.ANTIALIAS)
            img.save(path / 'images' / 'thumb' / ('thmb_' + file_name + '.jpg'))

        with open(path / 'images' / 'images.sa', 'w') as fw:
            fw.write(json.dumps(files_path))

        with open(path.joinpath('annotations.json'), 'w') as fw:
            json.dump(new_json, fw)

        with open(path / 'config.json', 'w') as fw:
            json.dump({"pathSeparator": os.sep, "os": sys.platform}, fw)

    def save_web_format(self, classes, files_dict):
        path = Path(self.output_dir)
        for key, value in files_dict.items():
            with open(path.joinpath(key), 'w') as fw:
                json.dump(value, fw, indent=2)

        with open(path.joinpath('classes', 'classes.json'), 'w') as fw:
            json.dump(classes, fw)

    def dump_output(self, classes, files_dict):
        if self.platform == 'Web':
            self.save_web_format(classes, files_dict)
        else:
            self.save_desktop_format(classes, files_dict)
