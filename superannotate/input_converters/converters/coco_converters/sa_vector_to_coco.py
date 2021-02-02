'''
SA to COCO conversion methods
'''
import logging
import threading

from .coco_api import _area, _merge, _polytoMask, _toBbox

from ....common import tqdm_converter

logger = logging.getLogger("superannotate-python-sdk")


def sa_vector_to_coco_object_detection(
    make_annotation, image_commons, instances, id_generator
):
    annotations_per_image = []
    image_info = image_commons.image_info

    for instance in instances:
        if instance['type'] != 'bbox':
            logger.warning(
                "Skipping '%s' type convertion during object_detection task",
                instance['type']
            )
            continue

        anno_id = next(id_generator)
        category_id = instance['classId']
        points = instance['points']
        for key in points:
            points[key] = round(points[key], 2)
        bbox = (
            points['x1'], points['y1'], points['x2'] - points['x1'],
            points['y2'] - points['y1']
        )
        polygons = bbox
        area = int((points['x2'] - points['x1']) * points['y2'] - points['y1'])

        annotation = make_annotation(
            category_id, image_info['id'], bbox, polygons, area, anno_id
        )
        annotations_per_image.append(annotation)

    return image_info, annotations_per_image


def sa_vector_to_coco_instance_segmentation(
    make_annotation, image_commons, instances, id_generator
):
    annotations_per_image = []
    grouped_polygons = {}

    image_info = image_commons.image_info
    id_ = -1
    for instance in instances:
        if instance['type'] != 'polygon':
            logger.warning(
                "Skipping '%s' type convertion during object_detection task",
                instance['type']
            )
            continue

        if instance['classId'] < 0:
            continue

        group_id = instance['groupId']

        if group_id == 0:
            group_id += id_
            id_ -= 1

        category_id = instance['classId']
        points = [round(point, 2) for point in instance['points']]
        grouped_polygons.setdefault(group_id, {}).setdefault(category_id,
                                                             []).append(points)

    for polygon_group in grouped_polygons.values():
        for cat_id, polygons in polygon_group.items():
            anno_id = next(id_generator)
            masks = _polytoMask(
                polygons, image_info['height'], image_info['width']
            )
            mask = _merge(masks)
            area = int(_area(mask))
            bbox = list(_toBbox(mask))
            annotation = make_annotation(
                cat_id, image_info['id'], bbox, polygons, area, anno_id
            )
            annotations_per_image.append(annotation)
    return (image_info, annotations_per_image)


def sa_vector_to_coco_keypoint_detection(
    jsons, id_generator, id_generator_anno, id_generator_img, make_image_info,
    total_num
):
    def __make_skeleton(template):
        res = [
            [connection['from'], connection['to']]
            for connection in template['connections']
        ]
        return res

    def __make_keypoints(template):
        int_dict = {
            int(key): value
            for key, value in template['pointLabels'].items()
        }

        res = [int_dict[i] for i in range(len(int_dict))]
        return res

    def __make_bbox(points):
        xs = [point['x'] for point in points]
        ys = [point['y'] for point in points]

        return [
            int(min(xs)),
            int(min(ys)),
            int(max(xs)) - int(min(xs)),
            int(max(ys)) - int(min(ys))
        ]

    def __make_annotations(template, id_generator, cat_id, image_id):
        keypoints = []

        for point in template['points']:
            keypoints += [round(point['x'], 2), round(point['y'], 2), 2]
        bbox = __make_bbox(template['points'])
        annotation = {
            'id': next(id_generator),
            'image_id': image_id,
            'iscrowd': 0,
            'bbox': bbox,
            'area': bbox[2] * bbox[3],
            'num_keypoints': len(template['points']),
            'keypoints': keypoints,
            'category_id': cat_id
        }

        return annotation

    template_names = set()
    categories = []
    annotations = []
    images = []

    images_converted = []
    images_not_converted = []
    finish_event = threading.Event()
    tqdm_thread = threading.Thread(
        target=tqdm_converter,
        args=(total_num, images_converted, images_not_converted, finish_event),
        daemon=True
    )
    logger.info('Converting to COCO JSON format')
    tqdm_thread.start()
    for json_ in jsons:
        json_data = json_['instances']
        for instance in json_data:
            if instance['type'] == 'template' and 'templateId' not in instance:
                logger.warning(
                    'There was a template with no "templateName". \
    This can happen if the template was deleted from superannotate.com. Ignoring this annotation'
                )
                continue

            if instance['type'] != 'template' or instance['templateId'
                                                         ] in template_names:
                continue
            if instance['pointLabels'] == {}:
                instance['pointLabels'] = {
                    x['id']: x['id']
                    for x in instance['points']
                }

            keypoints = []
            name = ""
            supercategory = ""
            id_ = 0
            try:
                template_names.add(str(instance['templateId']))
                skeleton = __make_skeleton(instance)
                keypoints = __make_keypoints(instance)
                id_ = next(id_generator)
                if "classId" in instance.keys():
                    supercategory = instance["classId"]
                else:
                    supercategory = str(instance["templateId"])
                if "className" in instance.keys():
                    name = str(instance["className"])
                else:
                    name = str(instance["templateId"])
            except Exception as e:
                logging.error(e)

            category_item = {
                'name': name,
                'supercategory': supercategory,
                'skeleton': skeleton,
                'keypoints': keypoints,
                'id': id_
            }
            categories.append(category_item)
        image_id = next(id_generator_img)
        image_info = make_image_info(
            json_['metadata']['name'], json_['metadata']['height'],
            json_['metadata']['width'], image_id
        )
        images.append(image_info)

        for instance in json_data:
            cat_id = None
            if instance['type'] == 'template':
                for cat in categories:
                    if cat["name"] == instance["className"]:
                        cat_id = cat['supercategory']

                annotation = __make_annotations(
                    instance, id_generator_anno, cat_id, image_info['id']
                )
                annotations.append(annotation)
        images_converted.append(json_data)
    finish_event.set()
    tqdm_thread.join()
    return (categories, annotations, images)
