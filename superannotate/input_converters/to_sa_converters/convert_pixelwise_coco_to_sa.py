import json
import numpy as np
import argparse
import os
import cv2
from panopticapi.utils import id2rgb


# Generates blue colors in range(n)
def blue_color_generator(n, hex_values=True):
    hex_colors = []
    for i in range(n):
        int_color = i * 15
        bgr_color = np.array(
            [
                int_color & 255, (int_color >> 8) & 255,
                (int_color >> 16) & 255, 255
            ],
            dtype=np.uint8
        )
        hex_color = '#' + "{:02x}".format(
            bgr_color[2]
        ) + "{:02x}".format(bgr_color[1], ) + "{:02x}".format(bgr_color[0])
        if hex_values:
            hex_colors.append(hex_color)
        else:
            hex_colors.append(hex_to_rgb(hex_color))
    return hex_colors


# Converts HEX values to RGB values
def hex_to_rgb(hex_string):
    h = hex_string.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# Converts RGB values to HEX values
def rgb_to_hex(rgb_tuple):
    return '#%02x%02x%02x' % rgb_tuple


parser = argparse.ArgumentParser()
parser.add_argument(
    "--coco-json", type=str, required=True, help="Argument must be JSON file"
)

p = parser.parse_args()
coco_path = p.coco_json
coco_path_folder, coco_path_file = os.path.split(coco_path)

with open(coco_path) as reader:
    coco_json = json.load(reader)

sa_dir = coco_path_file + "___formated"
os.makedirs(sa_dir, exist_ok=True)

hex_colors = blue_color_generator(len(coco_json["categories"]))

# creat classes json from coco categories
classes = []
classes_dir = os.path.join(sa_dir, "classes")
os.makedirs(classes_dir, exist_ok=True)
for i in range(len(hex_colors)):
    coco_cat = coco_json["categories"][i]
    dd = {
        "name": coco_cat["name"],
        "id": coco_cat["id"],
        "color": hex_colors[i],
        "attribute_groups": []
    }
    classes.append(dd)

with open(os.path.join(classes_dir, "classes.json"), "w") as writer:
    json.dump(classes, writer, indent=2)

# create blue mask and json
image_list = coco_json["images"]
annotate_list = coco_json["annotations"]

for image in image_list:
    img_name = os.path.splitext(image["file_name"])[0]
    for annotate in annotate_list:
        annot_name = os.path.splitext(annotate["file_name"])[0]
        if img_name == annot_name:
            img_cv = cv2.imread(
                os.path.join(
                    coco_path_folder, os.path.join("panoptic_masks", img_name + ".png")
                )
            )
            if img_cv is None:
                print(
                    "Error: '{}' file dosen't exist!".format(
                        os.path.join("panoptic_masks", img_name + ".png")
                    )
                )
                break

            img = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
            H, W, C = img.shape
            img = img.reshape((H * W, C))
            segments = annotate["segments_info"]
            hex_colors = blue_color_generator(len(segments))
            out_json = []
            for i, seg in enumerate(segments):
                img[np.all(img == id2rgb(seg["id"]),
                           axis=1)] = hex_to_rgb(hex_colors[i])
                dd = {
                    "classId": seg["category_id"],
                    "probability": 100,
                    "visible": True,
                    "parts": [{
                        "color": hex_colors[i]
                    }],
                    "attributes": [],
                    "attributeNames": [],
                    "imageId": annotate["image_id"]
                }
                out_json.append(dd)
            with open(
                os.path.join(sa_dir, img_name + ".jpg___pixel.json"), "w"
            ) as writer:
                json.dump(out_json, writer, indent=2)

            img = cv2.cvtColor(img.reshape((H,W,C)), cv2.COLOR_RGB2BGR)
            cv2.imwrite(os.path.join(sa_dir, img_name + ".jpg___save.png"), img)
