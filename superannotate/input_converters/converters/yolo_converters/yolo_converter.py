from pathlib import Path
import json
import time


class YOLOConverter(object):
    def __init__(self, args):
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
            cat_id_map[class_['id']] = idx + 2
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
        for file_name, json_data in files_dict.items():
            file_name = file_name.replace('___objects.json', '')
            for js_data in json_data:
                if 'classId' in js_data:
                    js_data['classId'] = cat_id_map[js_data['classId']]
            json_data.append(meta)
            new_json[file_name] = json_data
        with open(path.joinpath('annotations.json'), 'w') as fw:
            json.dump(new_json, fw)

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
