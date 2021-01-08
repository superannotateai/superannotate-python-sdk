import json
from pathlib import Path
import cv2
import numpy as np

from ..sa_json_helper import (_create_pixel_instance, _create_sa_json)

from ....common import hex_to_rgb, blue_color_generator, write_to_json


def sagemaker_instance_segmentation_to_sa_pixel(data_path, output_dir):
    img_mapping = {}
    try:
        img_map_file = open(data_path / 'output.manifest')
    except Exception as e:
        raise Exception("'output.manifest' file doesn't exist")

    for line in img_map_file:
        dd = json.loads(line)
        img_mapping[Path(dd['attribute-name-ref']).name] = Path(
            dd['source-ref']
        ).name

    json_list = data_path.glob('*.json')
    classes_ids = {}
    for json_file in json_list:
        data_json = json.load(open(json_file))
        for annotataion in data_json:
            if 'consolidatedAnnotation' not in annotataion.keys():
                print('Wrong json files')
                raise Exception
            mask_name = Path(
                annotataion['consolidatedAnnotation']['content']
                ['attribute-name-ref']
            ).name

            classes_dict = annotataion['consolidatedAnnotation']['content'][
                'attribute-name-ref-metadata']['internal-color-map']

            img = cv2.imread(str(data_path / mask_name.replace(':', '_')))
            H, W, _ = img.shape

            class_contours = {}
            num_of_contours = 0
            for key, _ in classes_dict.items():
                if classes_dict[key]['class-name'] == 'BACKGROUND':
                    continue

                if key not in classes_ids.keys():
                    classes_ids[key] = classes_dict[key]['class-name']

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
            file_name = '%s___pixel.json' % (img_mapping[mask_name])
            sa_metadata = {
                'name': img_mapping[mask_name],
                'width': W,
                'height': H
            }
            sa_instances = []
            sa_mask = np.zeros((H, W, 4))
            for name, contours in class_contours.items():
                parts = []
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
                    parts.append({'color': blue_colors[idx]})
                    idx += 1
                    sa_obj = _create_pixel_instance(parts, [], name)
                    sa_instances.append(sa_obj)
            sa_json = _create_sa_json(sa_instances, sa_metadata)
            write_to_json(output_dir / file_name, sa_json)
            cv2.imwrite(
                str(output_dir / (img_mapping[mask_name] + '___save.png')),
                sa_mask
            )
    return classes_ids
