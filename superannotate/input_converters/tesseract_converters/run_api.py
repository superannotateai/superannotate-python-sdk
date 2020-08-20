from ocr import ocr
import os

DATA_PATH = "./bus.4B"
TESS_OUT_PATH = "./tess_output"
SA_OUT_PATH = "./sa_output"
CONVERTION_VERBOSE = 0

ocr = ocr(DATA_PATH, TESS_OUT_PATH)
ocr.load_data()
ocr.predict(output_type='txt')
ocr.eval("char")
ocr.eval("word")
ocr.predict(output_type='json')
ocr.draw_bb()

TESS_OUT_JSON_PATH = TESS_OUT_PATH + "/jsons/"
os.system("python tesseract_to_sa_converter.py --input %s --output %s --verbose %s" %
          (TESS_OUT_JSON_PATH, SA_OUT_PATH, CONVERTION_VERBOSE))
