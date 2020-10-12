import json
import logging
import numpy as np
from PIL import Image
from glob import glob
from tqdm import tqdm
from pathlib import Path
from .util_classes import *
from datetime import datetime
from shapely.geometry import Polygon
from ..exceptions import SABaseException

logger = logging.getLogger('superannotate')
class Analyzer(object):
    """This class is used to compare predictions to ground truth annotations in superannotate vector format"""

    @property
    def area_threshold(self, ):
        return self._area_threshold


    @area_threshold.setter
    def area_threshold(self, value):
        if value <= 0:
            self._area_threshold = 0
            logger.warning('The area threshold should be a number between 0 and one. For meaningful results it should be larger than 0.5, it will now be set to 0')
            return

        if value >=1:
            self._area_threshold = 1
            logger.warning('The area threshold should be a number betwqeen 0 and one. For meaningful results it should be larger than 0.5, it will now be set to 1')

        self._area_theshold = value

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
    def __init__(self, gt_df, target_df):
        if gt_df is None or target_df is None:
            raise SABaseException('the source path {} or target path {} are not provided'.format(gt_df, target_df))

        self.class_names = []
        self.gt_df = gt_df
        self.target_df = target_df

        gt_classes_path = Path(self.gt_classes,'classes', 'classes.json')
        target_classes_path = Path(self.target_df,'classes', 'classes.json')

        if not gt_classes_path.is_file() or not target_classes_path.is_file():
            raise SABaseException('The classes json of either source or target object does not exist')

        if not self.__check_and_set_class_names(gt_classes_path, target_classes_path):
            raise SABaseException('The classes of the two projects are not the same')

        self.class_names = {self.class_names[i] : i for i in range(len(self.class_names))}

        self.confusion_matrix = ConfusionMatrix(self.class_names, self.gt_df, self.target_df)

        self._area_threshold = 0.6

        self.anno_to_polygon = {
            'bbox': self.__from_bbox_to_shapely,
            'polygon': self.__from_sa_polygon_to_shapely
        }
    def __repr__(self, ):
        res = 'ass_name: {}\n area_threshold: {}\n source path: {}\n target path: {}\n confusion matrix {}\n'.format(self.class_names, self._area_threshold, self.gt_df, self.target_df, self.confusion_matrix)
        res = None
        return res

    def __str__(self,):
       'Analyzer object with {} classes and area threshold {}'.format(len(self.class_names), self._area_threshold)

    def compare_all(self ):
        gt_df = Path(self.gt_df)

        files = gt_df.glob('*___objects.json')

        for file_ in files:
            target_file = Path(self.target_df, file_.parts[-1])
            source = json.load(open(file_))
            target = json.load(open(target_file))
            self.__compare_single(source, target, file_, method)
        return self.confusion_matrix

    def __from_bbox_to_shapely(self, bbox):

        raise NotImplementedError()

    def __from_sa_polygon_to_shapely(self, bbox):
        raise NotImplementedError()

    def __gather_annotations(self, source, type_):

        arr =[self.anno_to_polygon[type_](item) for item in source if type_ in ['bbox', 'polygon']]

        return arr

    def __compare_annotations(self, source, target):
        raise NotImplementedError

    def compare_single(source, target, file_):

        source_bboxes = self.__gather_annotations(source, 'bbox')
        target_bboxes = self.__gather_bboxes(target, 'bbox')

        source_polygons = self.__gather_annotations(source, 'polygon')
        target_polygons = self.__gather_annotations(target, 'polygon')

        self.__compare_annotations(source_bboxes, source_bboxes)
        self.__compare_annotations(source_polygons, target_polygons)


