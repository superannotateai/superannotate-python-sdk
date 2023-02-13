"""
"""
import logging
import threading
from pathlib import Path

from PIL import Image

from ....common import id2rgb
from ....common import tqdm_converter
from ....common import write_to_json
from .coco_converter import CocoBaseStrategy

logger = logging.getLogger("sa")


class CocoPanopticConverterStrategy(CocoBaseStrategy):
    def __init__(self, args):
        super().__init__(args)

    def _sa_to_coco_single(self, id_, annotation_json, id_generator):

        image_commons = self._prepare_single_image_commons(
            id_, annotation_json["metadata"]
        )
        res = self.conversion_algorithm(
            image_commons, annotation_json["instances"], id_generator
        )
        return res

    def sa_to_output_format(self):
        out_json = self._create_skeleton()
        out_json["categories"] = self._create_categories(
            self.export_root / "classes_mapper.json"
        )

        images = []
        annotations = []
        id_generator = self._make_id_generator()
        annot_id_generator = self._make_id_generator()

        jsons = self.make_anno_json_generator()
        images_converted = []
        images_not_converted = []
        total_num = self.get_num_total_images()
        finish_event = threading.Event()
        tqdm_thread = threading.Thread(
            target=tqdm_converter,
            args=(total_num, images_converted, images_not_converted, finish_event),
            daemon=True,
        )
        logger.info("Converting to COCO JSON format")
        tqdm_thread.start()
        for json_ in jsons:
            idx = next(annot_id_generator)
            res = self._sa_to_coco_single(idx, json_, id_generator)

            panoptic_mask = json_["metadata"]["panoptic_mask"]

            Image.fromarray(id2rgb(res[2])).save(panoptic_mask)

            annotation = {
                "image_id": res[0]["id"],
                "file_name": Path(panoptic_mask).name,
                "segments_info": res[1],
            }
            annotations.append(annotation)

            images.append(res[0])
            images_converted.append(json_)

        out_json["annotations"] = annotations
        out_json["images"] = images
        write_to_json(self.output_dir / f"{self.dataset_name}.json", out_json)
        finish_event.set()
        tqdm_thread.join()


class CocoObjectDetectionStrategy(CocoBaseStrategy):
    def __init__(self, args):
        super().__init__(args)

    def _sa_to_coco_single(self, id_, annotation_json, id_generator):

        image_commons = self._prepare_single_image_commons(
            id_, annotation_json["metadata"]
        )

        def make_annotation(category_id, image_id, bbox, segmentation, area, anno_id):
            if self.task == "object_detection":
                segmentation = [
                    [
                        bbox[0],
                        bbox[1],
                        bbox[0],
                        bbox[1] + bbox[3],
                        bbox[0] + bbox[2],
                        bbox[1] + bbox[3],
                        bbox[0] + bbox[2],
                        bbox[1],
                    ]
                ]
            annotation = {
                "id": anno_id,  # making sure ids are unique
                "image_id": image_id,
                "segmentation": segmentation,
                "iscrowd": 0,
                "bbox": bbox,
                "area": area,
                "category_id": category_id,
            }

            return annotation

        res = self.conversion_algorithm(
            make_annotation, image_commons, annotation_json["instances"], id_generator
        )
        return res

    def sa_to_output_format(self):
        out_json = self._create_skeleton()
        out_json["categories"] = self._create_categories(
            self.export_root / "classes_mapper.json"
        )

        images = []
        annotations = []
        id_generator = self._make_id_generator()
        annot_id_generator = self._make_id_generator()
        jsons = self.make_anno_json_generator()

        images_converted = []
        images_not_converted = []
        finish_event = threading.Event()
        total_num = self.get_num_total_images()
        tqdm_thread = threading.Thread(
            target=tqdm_converter,
            args=(total_num, images_converted, images_not_converted, finish_event),
            daemon=True,
        )
        logger.info("Converting to COCO JSON format")
        tqdm_thread.start()
        for json_ in jsons:
            idx = next(annot_id_generator)
            try:
                images_converted.append(json_)
                res = self._sa_to_coco_single(idx, json_, id_generator)
            except Exception as e:
                images_not_converted.append(json_)
                raise

            images.append(res[0])
            if len(res[1]) < 1:
                self.increase_converted_count()
            for ann in res[1]:
                annotations.append(ann)
        out_json["annotations"] = annotations
        out_json["images"] = images

        write_to_json(self.output_dir / f"{self.dataset_name}.json", out_json)
        finish_event.set()
        tqdm_thread.join()


class CocoKeypointDetectionStrategy(CocoBaseStrategy):
    def __init__(self, args):
        super().__init__(args)

    def sa_to_output_format(self):
        out_json = self._create_skeleton()
        jsons = self.make_anno_json_generator()

        total_num = self.get_num_total_images()
        id_generator = self._make_id_generator()
        id_generator_anno = self._make_id_generator()
        id_generator_img = self._make_id_generator()

        res = self.conversion_algorithm(
            jsons,
            id_generator,
            id_generator_anno,
            id_generator_img,
            self._make_image_info,
            total_num,
        )

        out_json["categories"] = res[0]
        out_json["annotations"] = res[1]
        out_json["images"] = res[2]
        write_to_json(self.output_dir / f"{self.dataset_name}.json", out_json)
        self.set_num_converted(len(out_json["images"]))
