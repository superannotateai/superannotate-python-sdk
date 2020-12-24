import cv2
import numpy as np
import os
import json

from .supervisely_helper import _base64_to_polygon, _create_attribute_list

from ..sa_json_helper import _create_pixel_instance

from ....common import hex_to_rgb, blue_color_generator


def supervisely_instance_segmentation_to_sa_pixel(
    json_files, class_id_map, output_path
):
    sa_jsons = {}
    for json_file in json_files:
        file_name = os.path.splitext(os.path.basename(json_file)
                                    )[0] + '___pixel.json'

        json_data = json.load(open(json_file))
        sa_loader = []

        H, W = json_data['size']['height'], json_data['size']['width']
        mask = np.zeros((H, W, 4))

        hex_colors = blue_color_generator(10 * len(json_data['objects']))
        index = 0
        for obj in json_data['objects']:
            if 'classTitle' in obj and obj['classTitle'] in class_id_map.keys():
                attributes = []
                if 'tags' in obj.keys():
                    attributes = _create_attribute_list(
                        obj['tags'], obj['classTitle'], class_id_map
                    )
                    parts = []
                    if obj['geometryType'] == 'bitmap':
                        segments = _base64_to_polygon(obj['bitmap']['data'])
                        for segment in segments:
                            ppoints = [
                                x + obj['bitmap']['origin'][0] if i %
                                2 == 0 else x + obj['bitmap']['origin'][1]
                                for i, x in enumerate(segment)
                            ]
                            bitmask = np.zeros((H, W)).astype(np.uint8)
                            pts = np.array(
                                [
                                    ppoints[2 * i:2 * (i + 1)]
                                    for i in range(len(ppoints) // 2)
                                ],
                                dtype=np.int32
                            )
                            cv2.fillPoly(bitmask, [pts], 1)
                            color = hex_to_rgb(hex_colors[index])
                            mask[bitmask == 1] = list(color[::-1]) + [255]
                            parts.append({'color': hex_colors[index]})
                            index += 1
                        cv2.imwrite(
                            str(
                                output_path / file_name.
                                replace('___pixel.json', '___save.png')
                            ), mask
                        )
                        sa_obj = _create_pixel_instance(
                            parts, attributes, obj['classTitle']
                        )
                        sa_loader.append(sa_obj)

        sa_jsons[file_name] = sa_loader
    return sa_jsons
