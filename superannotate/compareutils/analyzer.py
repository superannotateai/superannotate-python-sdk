import json
import logging
import numpy as np
from PIL import Image
from glob import glob
from tqdm import tqdm
from pathlib import Path
from copy import deepcopy
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

        gt_classes = source["class"].unique()
        target_classes = target["class"].unique()

        if len(target_classes) != len(gt_classes) or set(target_classes) != set(gt_classes):
            logger.info('The class names present in source and target dataframes are not the same')

        gt_classes = set(gt_classes).union(set(target_classes))
        self.class_names = gt_classes

        return True

    def __init__(self, gt_df, target_df):
        if gt_df is None or target_df is None:
            raise SABaseException('the source path {} or target path {} are not provided'.format(gt_df, target_df))

        self.class_names = []

        # Deepcopy the dataframes to change them as we like
        self.gt_df = deepcopy(gt_df)
        self.target_df = deepcopy(target_df)

        if not self.__check_and_set_class_names(self.gt_df, self.target_df):
            raise SABaseException('The classes of the two projects are not the same')
        self.class_names = list(self.class_names)
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

    def compare_all(self, method):

        src_bboxes = self.__transform_annotations(self.gt_df, 'bbox')
        target_bboxes = self.__transform_annotations(self.target_df, 'bbox')

        target_polygons = self.__transform_annotations(self.target_df, 'polygon')
        src_polygons = self.__transform_annotations(self.gt_df, 'polygon')

        src_bboxes.apply(lambda x: self.__compare_single_row(x, target_bboxes), axis = 1,)# args = target_bboxes)
        #src_polygons.apply(lambda x: self.__compare_single_row(x, target_polygons), axis = 1)
        return self.confusion_matrix

    def __from_bbox_to_shapely(self, bbox):
        bbox.meta["points"] = Polygon([(bbox.meta["points"]["x1"], bbox.meta["points"]["y1"]), (bbox.meta["points"]["x2"], bbox.meta["points"]["y1"]), (bbox.meta["points"]["x2"], bbox.meta["points"]["y2"]), (bbox.meta["points"]["x1"], bbox.meta["points"]["y2"])])

    def __append_fname_to_image_list(self, src_class, target_class, fname):

        if src_class not in self.confusion_matrix.confusion_image_map:
            self.confusion_matrix.confusion_image_map[src_class] = {}

        if target_class not in self.confusion_matrix.confusion_image_map[src_class]:
             self.confusion_matrix.confusion_image_map[src_class][target_class] = set()
        self.confusion_matrix.confusion_image_map[src_class][target_class].add(fname)

    def __from_sa_polygon_to_shapely(self, polygon):
        x = polygon.meta["points"][0::2]
        y = polygon.meta["points"][1::2]

        polygon.meta["points"] = Polygon(list(zip(x,y)))

    def __transform_annotations(self, source, type_):
        rows = source[source["type"] == type_]
        rows.apply(self.anno_to_polygon[type_], axis = 1)

        return rows

    def __compare_single_row(self, source_row, target_df):

        src_poly = source_row.meta["points"]
        backgroundQ = None
        i = self.class_names[source_row["class"]]
        target_df_roi = target_df[target_df["image_name"] == source_row['image_name']]
        for item in target_df_roi.itertuples():

            backgroundQ = True
            union_area = src_poly.union(item.meta["points"]).area
            intersection_area = src_poly.intersection(item.meta["points"]).area
            IoU = intersection_area / union_area

            if IoU >= self.area_threshold:
                new_row = {"ImageName":source_row["image_name"] ,"GTInstanceId":source_row["instance_id"], "TargetInstanceId": item.instance_id, "GTClass":source_row["class"], "TargetClass": item[2]}
                print(new_row)
                self.confusion_matrix.df = self.confusion_matrix.df.append(new_row, ignore_index = True)
                j = self.class_names[item[3]]
                self.confusion_matrix.confusion_matrix[i][j] += 1
                self.__append_fname_to_image_list(source_row['class'], item[3], item[1])
                backgroundQ = False

        if backgroundQ:
            self.confusion_matrix.confusion_matrix[i][-1] += 1



