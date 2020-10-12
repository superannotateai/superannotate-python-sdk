import json
import shutil
import numpy as np
from PIL import Image, ImageDraw
from tqdm import tqdm
from pathlib import Path
import plotly.figure_factory as ff

class ConfusionMatrix(object):
    """
    A class that describes the confusion matrix.
    It will have to export confused images, optionally draw annotations,
    and show the confusion matrix using plotly
    """

    def __init__(self, class_names, gt_path, target_path):

        self._N = len(class_names) + 1
        self.class_names = class_names
        self.confusion_matrix = np.zeros([self._N, self._N], dtype = np.uint8)
        self.confusion_image_map = {}
        self.gt_path = gt_path
        self.target_path = target_path



    def show(self, ):
        class_names = list(class_names.keys())
        class_names.append("NoClass")
        z_text = [[str(y) for y in x] for x in self.confusion_matrix]
        fig = ff.create_annotated_heatmap(self.confusion_matrix, x=class_names, y=class_names, annotation_text=z_text, colorscale='Viridis')

        fig.show()

    def __draw_from_one(self, img, json_data, name_pairs, color):

        for anno in json_data:
            if anno['type'] not in ['bbox', 'polygon'] or anno['className'] not in name_pairs:
                continue

            if anno['type'] == 'bbox':
                img =  Drawer.draw_bbox(img, anno['points'], color, anno['className'])
            else:
                img = Drawer.draw_poly(img, anno['points'], color,anno['className'])

        return img
    def draw(self, j_name, img_name, name_pairs):
        src_anno_data = json.load(open(j_name))

        img_name = Path(self.gt_path, img_name)
        img = Image.open(img_name)
        name_pairs = set(np.array([list(x) for x in name_pairs]).flatten())

        target_anno_path = Path(self.target_path, j_name.parts[-1])
        target_anno_data = json.load(open(target_anno_path))
        draw = ImageDraw.Draw(img)
        draw = self.__draw_from_one(draw, src_anno_data, name_pairs, (255,0,0))
        draw = self.__draw_from_one(draw, target_anno_data, name_pairs, (0,255,0))

        return img
    def export(self, name_pairs, export_dir, drawQ):
        fnames = []
        for pair in name_pairs:
            idx_1 = self.class_names[pair[0]]
            idx_2 = self.class_names[pair[1]]
            if idx_1 in self.confusion_image_map and idx_2 in self.confusion_image_map[idx_1]:
                fnames += list(self.confusion_image_map[idx_1][idx_2])
            elif idx_2 in self.confusion_image_map and idx_1 in self.confusion_image_map[idx_2]:
                fnames += list(self.confusion_image_map[idx_2][idx_1])
        export_dir = Path(export_dir)

        if not export_dir.is_dir():
            export_dir.mkdir(parents = True, exist_ok = True)

        for fname in fnames:
            img_name = fname.parts[-1][:-len("___objects.json")]
            try:
                target = Path(export_dir, fname.parts[-1])
                shutil.copy(fname, target)
                target = Path(export_dir, img_name)
                shutil.copy(fname, target)

                if not drawQ:
                    continue
                img = self.draw(fname,img_name, name_pairs)

                draw_dir = Path(export_dir, 'draw')
                draw_dir.mkdir(parents = True, exist_ok = True)
                img.save(Path(draw_dir, img_name + '___draw.jpg'))
            except Exception as e:
                print(e)
                pass


class BBox(object):

    def __init__(self, bbox, category_name):
        bbox = bbox[0]
        if bbox[2] > bbox[0]:
            self._R = [bbox[2], bbox[3]]
            self._L = [bbox[0], bbox[1]]
        else:
            self._R = [bbox[0], bbox[1]]
            self._L = [bbox[2], bbox[3]]

        self.width = abs(self._R[0] - self._L[0])
        self.height = abs(self._L[1] - self._R[1])
        self.category_name = category_name

class Mask(object):
    def __init__(self, mask, category_name):
        self.mask = mask
        self.category_name = category_name



class Drawer(object):
    @classmethod
    def draw_bbox(cls, img, bbox, color, class_name):
        img.rectangle([bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']], outline = color )
        fnt = ImageDraw.getfont()
        img.text([bbox['x1'], bbox['y1']], class_name, color)
        return img
    @classmethod
    def draw_poly(cls, img, poly, color, class_name):
        img.polygon(poly, color)
        return img

