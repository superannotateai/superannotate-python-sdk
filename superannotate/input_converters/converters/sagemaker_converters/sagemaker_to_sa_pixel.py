import os
import cv2
import json
from glob import glob
import numpy as np

from ....common import hex_to_rgb, blue_color_generator


def create_classes(classes):
    classes_loader = []
    for name, class_ in classes.items():
        cls_obj = {
            "id": class_['id'],
            "name": name,
            "color": class_['color'],
            "attribute_groups": []
        }
        classes_loader.append(cls_obj.copy())
    return classes_loader


def sagemaker_instance_segmentation_to_sa_pixel(data_path, main_key):
    img_mapping = {}
    try:
        img_map_file = open(os.path.join(data_path, 'output.manifest'))
    except Exception as e:
        raise Exception("'output.manifest' file doesn't exist")

    for line in img_map_file:
        dd = json.loads(line)
        img_mapping[os.path.basename(dd['attribute-name-ref'])
                   ] = os.path.basename(dd['source-ref'])

    json_list = glob(os.path.join(data_path, '*.json'))
    classes_ids = {}
    idx = 1
    sa_jsons = {}
    sa_masks = {}
    for json_file in json_list:
        data_json = json.load(open(json_file))
        for annotataion in data_json:
            if 'consolidatedAnnotation' not in annotataion.keys():
                print('Wrong json files')
                raise Exception
            mask_name = os.path.basename(
                annotataion['consolidatedAnnotation']['content']
                ['attribute-name-ref']
            )

            classes = {}
            classes_dict = annotataion['consolidatedAnnotation']['content'][
                'attribute-name-ref-metadata']['internal-color-map']

            img = cv2.imread(
                os.path.join(data_path, mask_name.replace(':', '_'))
            )
            H, W, C = img.shape

            class_contours = {}
            num_of_contours = 0
            for key in classes_dict.keys():
                if classes_dict[key]['class-name'] == 'BACKGROUND':
                    continue

                if classes_dict[key]['class-name'] not in classes_ids:
                    classes_ids[classes_dict[key]['class-name']] = {
                        'id': idx,
                        'color': classes_dict[key]['hex-color']
                    }
                    idx += 1

                bitmask = np.zeros((H, W), dtype=np.int8)
                bitmask[np.all(
                    img == list(hex_to_rgb(classes_dict[key]['hex-color'])
                               )[::-1],
                    axis=2
                )] = 255

                bitmask = bitmask.astype(np.uint8)
                contours, _ = cv2.findContours(
                    bitmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                class_contours[classes_dict[key]['class-name']] = contours
                num_of_contours += len(contours)

            blue_colors = blue_color_generator(num_of_contours)
            idx = 0
            sa_name = img_mapping[mask_name] + '___pixel.json'
            sa_loader = []
            sa_mask = np.zeros((H, W, C + 1))

            for name, contours in class_contours.items():
                sa_obj = {
                    'classId': classes_ids[name]['id'],
                    'className': name,
                    'probability': 100,
                    'attributes': [],
                    'locked': False,
                    'visible': True,
                    'groupId': 0
                }
                for contour in contours:
                    bitmask = np.zeros((H, W))
                    contour = contour.flatten().tolist()
                    pts = np.array(
                        [
                            contour[2 * i:2 * (i + 1)]
                            for i in range(len(contour) // 2)
                        ],
                        dtype=np.int32
                    )
                    cv2.fillPoly(bitmask, [pts], 1)
                    sa_mask[bitmask == 1
                           ] = list(hex_to_rgb(blue_colors[idx]))[::-1] + [255]
                    sa_obj['parts'] = {'color': blue_colors[idx]}
                    idx += 1
                    sa_loader.append(sa_obj.copy())
            sa_jsons[sa_name] = sa_loader
            sa_masks[img_mapping[mask_name] + '___save.png'] = sa_mask
    return sa_jsons, create_classes(classes_ids), sa_masks