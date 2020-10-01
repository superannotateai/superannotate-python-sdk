import json
import numpy as np
from PIL import Image
from glob import glob
from pathlib import Path
from tqdm import tqdm
from pycocotools import mask as cocomask
from datetime import datetime
from .util_classes import *
from ..common import SA_CM_COMPARE_FAST, SA_CM_COMPARE_ACCURATE
class Analyzer(object):
    """
        This class is used to compare predictions to ground truth annotations in
        superannotate annotations format.
    """

    area_threshold = 0.6
    def __init__(self, gt_path=None, target_path=None):
        if gt_path == None or target_path == None:
            raise AttributeError(
                'Please provide directories for both the predicted and ground truth annotations'
            )

        self.class_names = []
        self.gt_path = gt_path
        self.target_path = target_path

        gt_classes_path = Path(self.gt_path, "classes", "classes.json")
        target_classes_path = Path(self.target_path, "classes", "classes.json")

        if not gt_classes_path.is_file() or not target_classes_path.is_file():
            raise AttributeError(
                'The ground truth or predicted annotations do not have a classes.json file in correct folder'
            )

        if not self.__check_and_set_class_names(gt_classes_path, target_classes_path):
            raise AttributeError('The ground truth and predicted annotations have different classes')
        self.class_names = {self.class_names[i] : i for i in range(len(self.class_names))}
        self.confusion_matrix = ConfusionMatrix(self.class_names, self.gt_path, self.target_path)


    def __repr__(self, ):
        pass

    def __str__(self, ):
        pass


    def __check_and_set_class_names(self, source, target):
        gt_classes = None
        pred_classes = None

        with open(source) as fp:
            data = json.load(fp)
            gt_classes = [x["name"] for x in data]

        with open(target) as fp:
            data = json.load(fp)
            target_classes = [x["name"] for x in data]

        if len(target_classes) != len(gt_classes) or set(target_classes) != set(gt_classes):
            return False

        self.class_names = gt_classes

        return True

    def __group_by_id(self,sa_ann_json):
        cur_id_offset = -1
        grouped_polygons = {}
        grouped_bboxes = {}

        def __format_points(points):
            res = [0,0,0,0]

            if type(points) is list:
                return points
            res[0] = points["x1"]
            res[1] = points["y1"]
            res[2] = points["x2"]
            res[3] = points["y2"]
            return res

        for instance in sa_ann_json:
            if 'classId' not in instance or  instance['classId'] < 0:
                continue
            if instance['type'] not in ['polygon' ,'bbox']:
                continue
            group_id = instance['groupId']
            category_id = instance['className']
            if group_id == 0:
                group_id += cur_id_offset
                cur_id_offset -= 1
            try:
                points = [round(point,2) for point in __format_points(instance['points'])]
            except Exception as e:
                pass
            if len(points) > 4:
                grouped_polygons.setdefault(group_id,{}).setdefault(category_id,[]).append(points)
            else:
                grouped_bboxes.setdefault(group_id,{}).setdefault(category_id,[]).append(points)
        return grouped_polygons, grouped_bboxes

    def __get_bboxes(self,grouped_boxes):
        res = []
        for group_id in grouped_boxes:
            key = list(grouped_boxes[group_id].keys())[0]
            res.append(BBox(grouped_boxes[group_id][key], key))
        return res

    def __get_masks(self, grouped_polygons):
        max_ = 0
        masks = []
        for group_id in grouped_polygons:
            key = list(grouped_polygons[group_id].keys())[0]
            for item in grouped_polygons[group_id][key]:
                if max_ < max(item):
                    max_ = max(item)

        for polygon_group in grouped_polygons.values():
            for cat_name, polygons in polygon_group.items():

                coco_masks = cocomask.frPyObjects(polygons, max_, max_)
                coco_mask = cocomask.merge(coco_masks)
                mask = cocomask.decode(coco_mask)

                masks.append(Mask(np.array(mask),cat_name))
        return masks

    def __append_to_confusion_image_map(self,src_idx, target_idx, fname):

        if src_idx not in self.confusion_matrix.confusion_image_map:
            self.confusion_matrix.confusion_image_map[src_idx] = {}
        if target_idx not in self.confusion_matrix.confusion_image_map[src_idx]:
            self.confusion_matrix.confusion_image_map[src_idx][target_idx] = set()
        self.confusion_matrix.confusion_image_map[src_idx][target_idx].add(fname)

    def __compare_masks(self, grouped_src_poly, grouped_target_poly, fname):

        src_masks = self.__get_masks(grouped_src_poly)
        target_masks = self.__get_masks(grouped_src_poly)

        while src_masks:
            backgroundQ = True
            src_mask = src_masks[0]
            src_idx = self.class_names[src_mask.category_name]
            for target_mask in target_masks:
                full_area = sum((src_mask.mask | target_mask.mask).flatten())
                intersection_area = sum((src_mask.mask & target_mask.mask).flatten())
                IoU = intersection_area / full_area
                target_idx = self.class_names[src_mask.category_name]
                if IoU >= Analyzer.area_threshold:
                    backgroundQ = False
                    self.__append_to_confusion_image_map(src_idx, target_idx, fname)
                    self.confusion_matrix.confusion_matrix[src_idx][target_idx] += 1
            if backgroundQ:
                self.confusion_matrix[src_idx][-1] += 1
            src_masks.pop(0)

    def __compare_bboxes(self,src_bboxes, target_bboxes, fname):
        while src_bboxes:
            backgroundQ = True
            src_bbox= src_bboxes[0]
            src_idx = self.class_names[src_bbox.category_name]
            for target_bbox in target_bboxes:
                target_idx = self.class_names[target_bbox.category_name]
                IoU = self.calc_iou(src_bbox, target_bbox)
                if IoU > Analyzer.area_threshold:
                    backgroundQ = False
                    self.confusion_matrix.confusion_matrix[src_idx][target_idx] += 1
                    self.__append_to_confusion_image_map(src_idx, target_idx, fname)
            src_bboxes.pop(0)

    def __get_bboxes_from_grouped_poly(self, src_poly_groups):
        bboxes = []

        for poly_group in src_poly_groups:
            res = list(src_poly_groups[poly_group].keys())
            key = res[0]
            points = []
            for poly in src_poly_groups[poly_group][key]:
                points += poly

            min_x = min(points[::2])
            min_y = min(points[1::2])
            max_x = max(points[::2])
            max_y = max(points[1::2])
            c_bbox = BBox([[min_x, min_y, max_x, max_y]],key )
            bboxes.append(c_bbox)
        return bboxes

    def __compare_single(self,source, target, fname, method):
        start_time = datetime.now()
        grouped_src_poly, grouped_src_bbox = self.__group_by_id(source)
        grouped_target_poly, grouped_target_bbox = self.__group_by_id(target)

        if method == SA_CM_COMPARE_ACCURATE:
            self.__compare_masks(grouped_src_poly, grouped_target_poly, fname)

        src_bboxes = self.__get_bboxes(grouped_src_bbox)
        target_bboxes = self.__get_bboxes(grouped_target_bbox)

        self.__compare_bboxes(src_bboxes,target_bboxes, fname)

        if method == SA_CM_COMPARE_FAST:
            src_bboxes = self.__get_bboxes_from_grouped_poly(grouped_src_poly)
            target_bboxes = self.__get_bboxes_from_grouped_poly(grouped_target_poly)
            self.__compare_bboxes(src_bboxes, target_bboxes, fname)

    def compare_all(self,method ):
        gt_path = Path(self.gt_path)

        files = gt_path.glob('*___objects.json')

        for file_ in files:
            target_file = Path(self.target_path, file_.parts[-1])
            source = json.load(open(file_))
            target = json.load(open(target_file))
            self.__compare_single(source, target, file_, method)
        return self.confusion_matrix


    def calc_iou(self, bbox1, bbox2):
        w = 0
        h = 0
        if (bbox1._R[0] <= bbox2._L[0]) or (bbox2._R[0] <= bbox1._L[0]):
            return 0
        if (bbox1._R[1] <= bbox2._L[1] ) or (bbox2._R[1] <= bbox1._L[1]):
            return 0

        if bbox1._L[0] > bbox2._L[0]:
            w = bbox2._R[0] - bbox1._L[0]
        else:
            w = bbox1._R[0] - bbox2._L[0]

        if bbox1._L[1] <= bbox2._L[1]:
            h = abs(bbox2._L[1] - bbox1._R[1])
        else:
            h = abs(bbox2._L[1] - bbox2._R[1])

        intersection_area = abs(h * w)
        total_area = bbox1.height * bbox1.width + bbox2.height * bbox2.width - intersection_area

        IoU = intersection_area / total_area
        return IoU
