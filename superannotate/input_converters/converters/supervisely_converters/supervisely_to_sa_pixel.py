import numpy as np
import os
import json
import zlib
import base64
import cv2

from ....common import hex_to_rgb, blue_color_generator


# Converts bitmaps to polygon
def _base64_to_polygon(bitmap):
    z = zlib.decompress(base64.b64decode(bitmap))
    n = np.frombuffer(z, np.uint8)
    mask = cv2.imdecode(n, cv2.IMREAD_UNCHANGED)[:, :, 3].astype(bool)
    contours, _ = cv2.findContours(
        mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    segmentation = []

    for contour in contours:
        contour = contour.flatten().tolist()
        if len(contour) > 4:
            segmentation.append(contour)
        if len(segmentation) == 0:
            continue
    return segmentation


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
                    for tag in obj['tags']:
                        group_name = class_id_map[obj['classTitle']
                                                 ]['attr_group']['group_name']
                        attr_name = tag['name']
                        attributes.append(
                            {
                                'name': attr_name,
                                'groupName': group_name
                            }
                        )

                    sa_obj = {
                        'className': obj['classTitle'],
                        'attributes': attributes,
                        'probability': 100,
                        'locked': False,
                        'visible': True,
                        'parts': [],
                    }

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
                            sa_obj['parts'].append({'color': hex_colors[index]})
                            index += 1
                        cv2.imwrite(
                            str(
                                output_path / file_name.
                                replace('___pixel.json', '___save.png')
                            ), mask
                        )
                        sa_loader.append(sa_obj)

        sa_jsons[file_name] = sa_loader
    return sa_jsons
