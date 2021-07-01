'''
Sagemaker to SA conversion method
'''
import logging
import threading
import json
from pathlib import Path

from ..sa_json_helper import (_create_vector_instance, _create_sa_json)

from ....common import write_to_json, tqdm_converter

logger = logging.getLogger("superannotate-python-sdk")


def sagemaker_object_detection_to_sa_vector(data_path, main_key, output_dir):
    dataset_manifest = []
    try:
        img_map_file = open(data_path / 'output.manifest')
    except Exception as e:
        raise Exception("'output.manifest' file doesn't exist")

    for line in img_map_file:
        dataset_manifest.append(json.loads(line))

    json_list = list(data_path.glob('*.json'))
    classes_ids = {}
    images_converted = []
    images_not_converted = []
    finish_event = threading.Event()
    tqdm_thread = threading.Thread(
        target=tqdm_converter,
        args=(
            len(json_list), images_converted, images_not_converted, finish_event
        ),
        daemon=True
    )
    logger.info('Converting to SuperAnnotate JSON format')
    tqdm_thread.start()
    for json_file in json_list:
        data_json = json.load(open(json_file))
        for img in data_json:
            if 'consolidatedAnnotation' not in img.keys():
                logger.warning('Wrong json files')
                raise Exception

            manifest = dataset_manifest[int(img['datasetObjectId'])]
            file_name = '%s___objects.json' % Path(manifest['source-ref']).name

            classes = img['consolidatedAnnotation']['content'][
                main_key + '-metadata']['class-map']
            for key, value in classes.items():
                if key not in classes_ids.keys():
                    classes_ids[key] = value

            image_size = img['consolidatedAnnotation']['content'][main_key][
                'image_size'][0]

            sa_metadata = {
                'name': Path(manifest['source-ref']).name,
                'width': image_size['width'],
                'height': image_size['height']
            }

            annotations = img['consolidatedAnnotation']['content'][main_key][
                'annotations']
            sa_instances = []
            for annotation in annotations:
                points = (
                    annotation['left'], annotation['top'],
                    annotation['left'] + annotation['width'],
                    annotation['top'] + annotation['height']
                )
                sa_obj = _create_vector_instance(
                    'bbox', points, {}, [], classes[str(annotation['class_id'])]
                )
                sa_instances.append(sa_obj.copy())
            images_converted.append(Path(manifest['source-ref']).name)
            sa_json = _create_sa_json(sa_instances, sa_metadata)
            write_to_json(output_dir / file_name, sa_json)

    finish_event.set()
    tqdm_thread.join()
    return classes_ids
