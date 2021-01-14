from pathlib import Path
import cv2
import numpy as np

from .labelbox_helper import (
    image_downloader, _create_classes_id_map, _create_attributes_list
)

from ..sa_json_helper import (_create_pixel_instance, _create_sa_json)

from ....common import hex_to_rgb, blue_color_generator, write_to_json


def labelbox_instance_segmentation_to_sa_pixel(
    json_data, output_dir, input_dir
):
    classes = _create_classes_id_map(json_data)
    for data in json_data:
        file_name = data['External ID'] + '___pixel.json'
        mask_name = data['External ID'] + '___save.png'
        sa_metadata = {'name': data['External ID']}
        if 'objects' not in data['Label'].keys():
            sa_json = _create_sa_json([], sa_metadata)
            write_to_json(output_dir / file_name, sa_json)
            continue

        instances = data["Label"]["objects"]
        sa_instances = []
        blue_colors = blue_color_generator(len(instances))

        for i, instance in enumerate(instances):
            class_name = instance["value"]
            attributes = []
            if 'classifications' in instance.keys():
                attributes = _create_attributes_list(
                    instance['classifications']
                )

            if 'bbox' in instance.keys() or 'polygon' in instance.keys(
            ) or 'line' in instance.keys() or 'point' in instance.keys():
                continue

            bitmask_name = '%s.png' % instance['featureId']
            downloaded = image_downloader(instance['instanceURI'], bitmask_name)
            if downloaded:
                mask = cv2.imread(bitmask_name)
            else:
                mask = cv2.imread(str(input_dir / 'bitmasks' / bitmask_name))
                bitmask_name = output_dir / bitmask_name

            if isinstance(mask, type(None)):
                continue

            if i == 0:
                H, W, _ = mask.shape
                sa_metadata['width'] = W
                sa_metadata['height'] = H
                sa_mask = np.zeros((H, W, 4))
            sa_mask[np.all(mask == [255, 255, 255], axis=2)
                   ] = list(hex_to_rgb(blue_colors[i]))[::-1] + [255]

            parts = [{'color': blue_colors[i]}]
            sa_obj = _create_pixel_instance(parts, attributes, class_name)

            sa_instances.append(sa_obj.copy())
            Path(bitmask_name).unlink()

        sa_json = _create_sa_json(sa_instances, sa_metadata)
        write_to_json(output_dir / file_name, sa_json)
        cv2.imwrite(str(output_dir / mask_name), sa_mask)
    return classes
