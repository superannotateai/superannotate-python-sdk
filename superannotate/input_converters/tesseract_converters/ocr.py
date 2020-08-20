import os
import json
from pytesseract import image_to_data, image_to_string, Output

from ocr_utils import list_files_path, get_files_list
from eval_utils import get_accuracy

from PIL import Image, ImageDraw, ImageFont


class ocr:
    def __init__(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir

        self.input_image_list = []
        self.output_image_list = []

    def load_data(self):
        files_path = list_files_path(self.input_dir)
        self.input_image_list = get_files_list(files_path)

        os.makedirs(os.path.join(self.output_dir, 'texts'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'images'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'jsons'), exist_ok=True)

        for im in self.input_image_list:
            base_name = os.path.basename(im)
            file_name = os.path.splitext(base_name)[0] + "___tess."
            self.output_image_list.append(file_name)

    def predict(self, output_type='txt'):
        for im_in, im_out in zip(self.input_image_list, self.output_image_list):
            if output_type == 'txt':
                output_path = os.path.join(
                    os.path.join(self.output_dir, 'texts'), im_out
                ) + 'txt'
                tf = open(output_path, "wt")
                result = image_to_string(im_in + "tif", config='--oem 1')
                tf.write(result)
                tf.close()
            elif output_type == 'json':
                output_path = os.path.join(
                    os.path.join(self.output_dir, 'jsons'), im_out
                ) + 'json'
                tf = open(output_path, "w")
                dd = image_to_data(im_in + "tif", output_type=Output.DICT)
                json.dump(dd, tf, indent=2)
                tf.close()
            else:
                print("ERROR: Unknown format!")

    def eval(self, method="char"):
        accuracy = []
        for gt, of in zip(self.input_image_list, self.output_image_list):
            # output_path = self.output_dir + "/texts/" + of + "txt"
            output_path = os.path.join(
                os.path.join(self.output_dir, "texts"), of
            ) + "txt"
            accuracy.append(get_accuracy(gt + "txt", output_path, method))

        try:
            print(
                "%s based accuracy : %.2f" %
                (method, sum(accuracy) / len(accuracy))
            )
        except TypeError:
            print("ERROR: Can't measure accuracy!")

    def draw_bb(self):
        for im_in, im_out in zip(self.input_image_list, self.output_image_list):
            img = Image.open(im_in + 'tif').convert("RGB")
            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype('Pillow/Tests/fonts/FreeMono.ttf', 40)

            json_path = os.path.join(
                os.path.join(self.output_dir, 'jsons'), im_out
            ) + 'json'
            tf = open(json_path, "r")
            file_json = json.load(tf)

            for i in range(len(file_json["level"])):
                if file_json["text"][i] != "":
                    x1 = file_json["left"][i]
                    y1 = file_json["top"][i]
                    x2 = file_json["left"][i] + file_json["width"][i]
                    y2 = file_json["top"][i] + file_json["height"][i]

                    draw.text(
                        (x1, y1), file_json["text"][i], fill='red', font=font
                    )
                    draw.rectangle(((x1, y1), (x2, y2)), outline='red')

            output_path = os.path.join(
                os.path.join(self.output_dir, 'images'), im_out
            ) + 'jpg'
            img.save(output_path)