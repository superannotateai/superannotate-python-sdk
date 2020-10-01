import glob
import json
import logging
import os
import shutil
import time

from tqdm import tqdm


def _merge_jsons(input_dir, output_dir):
    cat_id_map = {}
    classes_json = json.load(
        open(os.path.join(input_dir, "classes", "classes.json"))
    )

    new_classes = []
    for idx, class_ in enumerate(classes_json):
        cat_id_map[class_["id"]] = idx + 2
        class_["id"] = idx + 2
        new_classes.append(class_)

    files = glob.glob(os.path.join(input_dir, "*.json"))
    merged_json = {}
    os.makedirs(output_dir)
    for f in tqdm(files, "Merging files"):
        json_data = json.load(open(f))
        meta = {
            "type": "meta",
            "name": "lastAction",
            "timestamp": int(round(time.time() * 1000))
        }
        for js_data in json_data:
            if "classId" in js_data:
                js_data["classId"] = cat_id_map[js_data["classId"]]
        json_data.append(meta)
        file_name = os.path.split(f)[1].replace("___objects.json", "")
        merged_json[file_name] = json_data
    with open(
        os.path.join(output_dir, "annotations.json"), "w"
    ) as final_json_file:
        json.dump(merged_json, final_json_file, indent=2)

    with open(os.path.join(output_dir, "classes.json"), "w") as fw:
        json.dump(classes_json, fw, indent=2)


def _split_json(input_dir, output_dir):
    os.makedirs(output_dir)
    json_data = json.load(open(os.path.join(input_dir, "annotations.json")))
    images = json_data.keys()
    for img in images:
        annotations = json_data[img]
        objects = []
        for annot in annotations:
            objects.append(annot)

        with open(os.path.join(output_dir, img + "___objects.json"), "w") as fw:
            json.dump(objects, fw, indent=2)
    os.makedirs(os.path.join(output_dir, "classes"))
    shutil.copy(
        os.path.join(input_dir, "classes.json"),
        os.path.join(output_dir, "classes", "classes.json")
    )


def sa_conversion(input_dir, output_dir, input_platform):
    if input_platform == "Web":
        for file_name in os.listdir(input_dir):
            if '___pixel.json' in file_name:
                logging.error(
                    "Desktop platform doesn't support 'Pixel' projects"
                )
                break
        _merge_jsons(input_dir, output_dir)
    elif input_platform == 'Desktop':
        _split_json(input_dir, output_dir)
    else:
        logging.error("Please enter valid platform: 'Desktop' or 'Web'")
