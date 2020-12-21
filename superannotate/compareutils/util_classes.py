import json
import shutil
import numpy as np
from PIL import Image, ImageDraw
from tqdm import tqdm
from pathlib import Path
import plotly.figure_factory as ff
import pandas as pd
import logging
import cv2
import os

logger = logging.getLogger('superannotate')
class ConfusionMatrix(object):
    """
    A class that describes the confusion matrix.
    It will have to export confused images, optionally draw annotations,
    and show the confusion matrix using plotly
    """

    def __init__(self, class_names ):

        self._N = len(class_names) + 1
        self.class_names = class_names
        self.confusion_matrix = None
        self.df = pd.DataFrame(columns = ["ImageName", "GTInstanceId", "TargetInstanceId", "GTClass", "TargetClass", "TargetGeometry", "GTGeometry"])
        self.class_names['SA_Background'] = len(self.class_names)
    def show(self, ):

        if self.confusion_matrix is None:
            logger.warning("Confusion matrix does not yet exist. Please run create_confusion_matrix function of this object")
            return

        class_names = list(self.class_names.keys())
        z_text = [[str(y) for y in x] for x in self.confusion_matrix]
        fig = ff.create_annotated_heatmap(self.confusion_matrix, x=class_names, y=class_names, annotation_text=z_text, colorscale='Viridis')

        fig.show()

    def create_confusion_matrix(self):
        self.confusion_matrix = np.zeros([self._N, self._N], dtype = np.uint8)
        for row in self.df.itertuples():
            i = self.class_names[row.GTClass]
            j = self.class_names[row.TargetClass]
            self.confusion_matrix[i][j] += 1
            if i != j:
                self.confusion_matrix[j][i] += 1


    def __reshape_poly_to_cv_format(self, geometry):

        def reshape_lst(lst):
            new_lst = [[geometry[i], geometry[i+1]] for i in range(0, len(lst) - 1, 2)]
            return new_lst

        if type(geometry) is dict:
            geometry = [geometry["x1"], geometry["y1"], geometry["x1"], geometry["y2"], geometry["x2"], geometry["y2"], geometry["x2"], geometry["y1"]]
        geometry = [int(max(0, x)) for x in geometry]
        geometry = np.array(reshape_lst(geometry))
        return geometry

    def export(self, dataframe, image_src_folder, output_folder,thickness = 2, annotation_type = None):
        os.makedirs(output_folder, exist_ok = True)
        for item in dataframe.itertuples():
            image = cv2.imread(os.path.join(image_src_folder, item.ImageName), cv2.IMREAD_UNCHANGED)
            source_poly_points = self.__reshape_poly_to_cv_format(item.GTGeometry)
            target_poly_points = self.__reshape_poly_to_cv_format(item.TargetGeometry)
            image = cv2.polylines(image, [source_poly_points], False,  (0,255,0), thickness = thickness)
            image = cv2.putText(image, item.GTClass, tuple(source_poly_points[0]), fontFace = 2, fontScale = 0.5, color = (0,255,0 ))
            image = cv2.polylines(image, [target_poly_points], True, (255,0,0), thickness = thickness)
            image = cv2.putText(image, item.TargetClass, tuple(target_poly_points[0]), fontFace = 2,fontScale = 0.5, color =(255,0,0))


            cv2.imwrite(os.path.join(output_folder, item.ImageName), image)

