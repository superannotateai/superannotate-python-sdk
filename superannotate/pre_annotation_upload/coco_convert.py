import json
from pycocotools.coco import COCO
import cv2
import numpy as np
import os
             

def get_jsons_dict(coco_json_path):
    loader = []
    res={}
    json_data = json.load(open(coco_json_path))
    for annot in json_data['annotations']:
        for cat in json_data['categories']:
            if annot['iscrowd'] == 1:
                try:
                    annot['segmentation'] = rle_to_polygon(coco_json_path,annot)
                except IndexError:
                    print("List index out of range")
            if cat['id'] == annot['category_id']:
                sa_dict_bbox = {
                    'type': 'bbox',
                    'points':
                        {
                            'x1': annot['bbox'][0],
                            'y1': annot['bbox'][1],
                            'x2': annot['bbox'][0] + annot['bbox'][2],
                            'y2': annot['bbox'][1] + annot['bbox'][3]
                        },
                    'className': cat['name'],
                    'classId': cat['id'],
                    'attributes': [],
                    'probability': 100,
                    'locked': False,
                    'visible': True,
                    'groupId': annot['id'],
                    'imageId': annot['image_id']
                }

                sa_polygon_loader = [
                    {
                        'type': 'polygon',
                        'points': annot['segmentation'][p],
                        'className': cat['name'],
                        'classId': cat['id'],
                        'attributes': [],
                        'probability': 100,
                        'locked': False,
                        'visible': True,
                        'groupId': annot['id'],
                        'imageId': annot['image_id']
                    } for p in range(len(annot['segmentation']))
                ]

                for img in json_data['images']:
                    for polygon in sa_polygon_loader:
                        if polygon['imageId'] == img['id']:
                            loader.append((img['id'], polygon))
                        if sa_dict_bbox['imageId'] == img['id']:
                            loader.append((img['id'], sa_dict_bbox))

    for img in json_data['images']:
        f_loader = []
        for img_id, img_data in loader:
            if img['id'] == img_id:
                f_loader.append(img_data)
                res[img['file_name']] = [i for n, i in enumerate(f_loader) if i not in f_loader[n + 1:]]
    
    return res
                    


# Converts RLE format to polygon segmentation for object detection and keypoints
def rle_to_polygon(coco_json_path,annotation):
    coco = COCO(coco_json_path)
    binary_mask = coco.annToMask(annotation)
    contours, hierarchy = cv2.findContours(
        binary_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    segmentation = []
    for contour in contours:
        contour = contour.flatten().tolist()
        if len(contour) > 4:
            segmentation.append(contour)
        if len(segmentation) == 0:
            continue
    print(len(segmentation))
    return segmentation
