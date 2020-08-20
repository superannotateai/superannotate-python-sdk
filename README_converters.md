# Python conversion scripts between annotate.online format and other common formats.

## Table of Contents 
* [Installation](#installation)
* [Usage](#usage)
  * [Activate envirement](#activate-envirement)
  * [Tests](#tests)
* [To annotate.online json format](#to-annotate-format)
  * [From COCO output to annotate.online input](#coco-to-annotate)
  * [From Pascal VOC output to annotate.online input](#voc-to-annotate)
* [From annotate.online json format](#from-annotate-format)
  * [From annotate.online output to COCO input](#annotate-to-coco)
* [Tesseract OCR, with convertion to annotate.online](#tesseract-to-annotate)
* [Questions and Issues](#questions-and-issues)
<!-- * [References](#references) -->

## Installation

Run `bash install.sh`. This adds python virtualenv `venv_sa_conv` and
installs required packages.

## Usage

### Activate envirement
You need to activate python virtualenv with `source venv_sa_conv/bin/activate` beforehand.

### Tests

`annotateonline-input-converters/tests` contains few examples that can be helpful.

## To annotate.online json format <a name="to-annotate-format"></a>

Below we have few converter which can help you to convert popular output json formats to annotate.online json format. 

### *From* COCO output *to* annotate.online input <a name="coco-to-annotate"></a>

By following this [link](http://cocodataset.org/#format-results) you can find COCO dataset's result formats for object detection, panoptic segmentation and keypoint detection tasks.
By running [coco_to_sa.py](https://github.com/superannotateai/annotateonline-input-converters/blob/master/to_sa_converters/coco_to_sa.py) file you can convert COCO's result formats to annotate.online formats(vector or pixelwise segmentation depending on the type).
```
usage: coco_to_sa.py [-h] --coco-json COCO_JSON [--pixelwise {False,True}]
```
```
optional arguments:
  -h, --help            show this help message and exit
  --coco-json COCO_JSON
                        Argument must be JSON file
  --pixelwise {False,True}
                        Convert panoptic mask pixelwise
```
**Note**: For conversation from COCO's object detection or keypoint detection tasks result formats to annotate.online's vector type all you need is COCO's single JSON file, but for panoptic segmentation -> pixelwise segmentation you also need annotated png images in the folder name `panoptic_masks`. [--pixelwise] argument should be used only during panoptic conversion.

    python3 coco_to_sa.py --coco-json <input_coco_json> --pixelwise <{True,False}>
    
**Note**: COCO_JSON file's name should contain one of these keywords: `instances` if task is object detection, `keypoints` if task is keypoint detection and `panoptic` if task is panoptic segmentation! 


#### *Examples*

Here we present few examples. COCO json example is in `../tests/toAnnotateOnline/fromCocoToAnnotateOnline/` folder. Running converter will create new folder in that folder with following name `[COCO_JSON_NAME]___formated` which will contain all outputs. 

<!-- ##### **Object Detection** -->

*Example 1.1* : Object detection
```
    python3 coco_to_sa.py --coco-json ../tests/toAnnotateOnline/fromCocoToAnnotateOnline/instances_test.json
```

<!-- **Note**: This command will create new `instances_test.json__formated` directory in `./tests/toAnnotateOnline/fromCocoToAnnotateOnline/` which will contain original images
and their corresponding JSON files in annotate.online format. Besides, it will also be created `classes` directory 
in `./tests/toAnnotateOnline/fromCocoToAnnotateOnline/instances_test.json__formated/`, which will contain `classes.json`.
 -->
<!-- ##### **Keypoint Detection** -->

*Example 1.2* : Keypoint Detection
```
    python3 coco_to_sa.py --coco-json ../tests/toAnnotateOnline/fromCocoToAnnotateOnline/person_keypoints_test.json
```
<!-- **Note**: This command will create new `person_keypoints_test.json__formated` directory in `../tests/toAnnotateOnline/fromCocoToAnnotateOnline/` which will contain original images and their corresponding JSON files in annotate.online format. Besides, it will also be created `classes` directory in `../tests/toAnnotateOnline/fromCocoToAnnotateOnline/person_keypoints_test.json__formated/`, which will contain `classes.json`.
 -->
<!-- ##### **Panoptic segmentation** -->


*Example 1.3* : Panoptic segmentation

**Reminder**: In addition to the `COCO_JSON` file you must also have a folder named `panoptic_masks` in the same directory, which will contain panoptic segmentation's png masks. 

```
    python3 coco_to_sa.py --coco-json ../tests/toAnnotateOnline/fromCocoToAnnotateOnline/panoptic_test.json --pixelwise False
```

<!-- **Note**: This command at first  will create new `panoptic_test.json__formated` directory in `../tests/toAnnotateOnline/fromCocoToAnnotateOnline/` which will contain original images and their corresponding JSON files in annotate.online format and then will rename and move png masks from `../tests/toAnnotateOnline/fromCocoToAnnotateOnline/panoptic_masks/` to `../tests/toAnnotateOnline/fromCocoToAnnotateOnline/panoptic_test.json__formated/`. Besides, it will also be created `classes` directory in `../tests/toAnnotateOnline/fromCocoToAnnotateOnline/panoptic_test.json__formated/`, which will contain `classes.json`.
 -->

<!-- ##### **Panoptic segmentation 2** -->

*Example 1.4* : Panoptic segmentation

```
    python3 coco_to_sa.py --coco-json ../tests/toAnnotateOnline/fromCocoToAnnotateOnline/panoptic_test.json --pixelwise True
```
**Note**: This example differs from *Examples 3*, that this one also creates blue masks. 


### *From* Pascal VOC output *to* annotate.online input format <a name="voc-to-annotate"></a>

All information about Pascal VOC challenge and format you can find [here](http://host.robots.ox.ac.uk/pascal/VOC/). We mainly focus on 2 challenges: segmentation and object detection.

*please note*: We only support conversion from Pascal VOC format to annotate.online's vector format!
```
usage: pascalvoc_to_sa.py [-h] --pvoc-dir PVOC_DIR [-fd] [-fs]
```
```
optional arguments:
  -h, --help           show this help message and exit
  --pvoc-dir PVOC_DIR  Path of the directory, which contains all output data
                       of Pascal VOC
  -fd                  Set if you want to convert from VOC's detection format
  -fs                  Set if you want to convert from VOC's segmentation
                       format
```

<!-- ##### *From* VOC detection format *to* annotate.online vector format -->

### *Examples*

VOC2012 dataset example can be found in  `../tests/toAnnotateOnline/fromPascalVOCToAnnotateOnline/VOC2012/` folder. Converter creates folder with the name `[PVOC_DIR]__converted_from_[TYPE]`. [TYPE] is either `segmentation` or `detection`, depending which `-fs` or `-fd` argument will be used.

*Example 2.1* : VOC detection 


<!-- *Usage*
```
python3 pascalvoc_to_sa.py --pvoc-dir PVOC_DIR [-fd]
```
 -->
```
python3 pascalvoc_to_sa.py --pvoc-dir ../tests/toAnnotateOnline/fromPascalVOCToAnnotateOnline/VOC2012/ -fd
```

**Note**: `-fd` uses `detection` it means annotate.online's JSONs will contain only bboxes.


*Example 2.2* : VOC segmentation


<!-- ##### *From* VOC segmentation format *to* annotate.online vector format -->


<!-- *Usage*
```
python3 pascalvoc_to_sa.py --pvoc-dir PVOC_DIR [-fs]
```
 -->
<!-- *Example* -->

```
python3 pascalvoc_to_sa.py --pvoc-dir ../tests/toAnnotateOnline/fromPascalVOCToAnnotateOnline/VOC2012/ -fs
```
**Note**: `-fs` uses `segmentation` it means annotate.online's JSONs will contain only polygons.


## From annotate.online json format <a name="from-annotate-format"></a>

### *From* annotate.online output *to* COCO input format <a name="annotate-to-coco"></a>

There are 5 dataset formats that coco dataset supports, they are accessible [here](http://cocodataset.org/#format-data). We support several conversions from annotate.online formats to coco dataset formats. The command to do so is as follows:
```
usage: sa_to_coco.py [-h] [-is INPUT_IMAGES_SOURCE]
                     [-sr TRAIN_VAL_SPLIT_RATIO] [-ptype PROJECT_TYPE]
                     [-t TASK] [-dn DATASET_NAME] [-od OUTPUT_DIR] [-cp COPYQ]
```
```
optional arguments:
  -h, --help            show this help message and exit
  -is INPUT_IMAGES_SOURCE, --input_images_source INPUT_IMAGES_SOURCE
                        The folder where images and thei corresponding
                        annotation json files are located
  -sr TRAIN_VAL_SPLIT_RATIO, --train_val_split_ratio TRAIN_VAL_SPLIT_RATIO
                        What percentage of input images should be in train set
  -ptype PROJECT_TYPE, --project_type PROJECT_TYPE
                        The type of the annotate.online project can be vector
                        or pixel
  -t TASK, --task TASK  The output format of the converted file, this
                        corresponds to one of 5 coco tasks
  -dn DATASET_NAME, --dataset_name DATASET_NAME
                        The name of the dataset
  -od OUTPUT_DIR, --output_dir OUTPUT_DIR
                        The output folder for the coco json files test/train
                        images
  -cp COPYQ, --copyQ COPYQ
                        Move or copy source images to corresponding test and
                        train folders possible values are True or False. True copies the files
``````

**IMPORTANT:** Running this command will move or copy images from source folder. It will create two folders with names "test_set" and "train_set" and move images correspondingly.

#### Panoptic segmentation
```
python3 sa_to_coco.py -is [path_to_images] -sr [ratio] -ptype pixel -t panoptic_segmentation -dn [dataset_name] -od [output_directory] -cp [copyQ]
```

*please note*: conversion to coco dataset format for panoptic segmentation task is only supported for projects of type pixel in annotate.online

**Note**: You should have all your images their corresponding `save.png`, `pixel.json` and `lores.jpg` files in one folder as well as the `classes.json` file in the same folder.


*Example*
```
python sa_to_coco.py -is ./tests/fromAnnotateOnline/cats_dogs_pixel_panoptic_segm -sr 80 -ptype pixel -t panoptic_segmentation -dn test_panoptic -od output_pan -cp True

```

#### Instance segmentation

```
python3 sa_to_coco.py -is [path_to_images] -sr [ratio] -ptype [vector or pixel] -t instance_segmentation -dn [dataset_name] -od [output_directory] -cp [copyQ]
```

**Note**: if your project is of type 'pixel' you should have all your images their corresponding `save.png`, `pixel.json` and `lores.jpg` files in one folder as well as the `classes.json` file in the same folder. 
If your project is of type  'vector' then you will need all your images their corresponding `lores.jpg`, `objects.json` and `classes.json` files in the same folder

*Example*

```
python sa_to_coco.py -is ./tests/fromAnnotateOnline/cats_dogs_pixel_instance_segm -sr 80 -ptype pixel -t instance_segmentation -dn test_instance -od output_inst -cp True

```

Projects that have type vector with polygon annotations can still be converted to coco format 

```
python sa_to_coco.py -is ./tests/fromAnnotateOnline/cats_dogs_vector_instance_segm -sr 80 -ptype vector -t instance_segmentation -dn test_instance -od output_inst -cp True

```
#### Object detection 

Object detecion is similar to instance segmentation in the sense that it can be used with both
vector and pixel SA annotations. This function takes the bounding box of the instance and uses it 
as a segmentation mask, effectively turning instance segmentation task into bounding-box detection
problem. 

The command is:


```
python sa_to_coco.py -is [path_to_images] -sr [ratio] -ptype [project type] -t object_detection -dn [dataset_name] -od [output_directory] -cp [CopyQ]

```
*example*

```
python sa_to_coco.py -is ./tests/fromAnnotateOnline/cats_dogs_pixel_instance_segm -sr 80 -ptype pixel -t object_detection -dn test_object -od output_objects -cp True

```


#### Keypoint detection

```
python3 sa_to_coco.py -is [path_to_images] -sr [ratio] -ptype vector -t keypoint_detection -dn [dataset_name] -od [output_directory] -cp [copyQ] -od [output_directory] -cp [copyQ]
```

*please note*: conversion to coco dataset format for keypoint detection task is only supported for projects of type 'vector' in annotate.online. Furthermore each template should fully describe an object. 

**Note**: You should have all your images their corresponding `objects.json` files in one folder as well as the `classes.json` file in the same folder. 

*Example*

```
python sa_to_coco.py -is ./tests/fromAnnotateOnline/cats_dogs_vector_keypoint_det -sr 80 -ptype vector -t keypoint_detection -dn test_keyp -od output_keyp -cp True

```

## Tesseract OCR, with convertion to annotate.online <a name="tesseract-to-annotate"></a>

**Note** : `ocreval` metric was used for evaluation of accuracy. Make shure you have installed it before running. [here](https://github.com/eddieantonio/ocreval) 

*please note*: `tesseract_converters` folder contains full pipline to run tesseract ocr on any document and convert it to annotate.online json file. Before running the `run_api.py` modify `DATA_PATH` variable. Test datasets exist on `bus.4B` folder from isri-ocr-evolution-tools project [here](https://code.google.com/archive/p/isri-ocr-evaluation-tools/downloads?page=1).

```
python3 run_api.py 
```

*please note*: You can use only 'tesseract_to_sa_converter.py' separatly, if you allready have tesseract json files. Make sure your data images name have following structure: `[IMAGE_NAME]___[REST_OF_NAME].json`  

```
Usage: python3 tesseract_to_sa_converter.py [-h] --input INPUT [--output OUTPUT]
[--verbose {0,1,2}]
```
```
optional arguments:
  -h, --help         show this help message and exit
  --input INPUT      Path to input files or folder with tesseract dict format.
                     File name structure [IMAGE_NAME]___tess.json
  --output OUTPUT    Path to output folder. File name structure
                     [IMAGE_NAME]___objects.json
  --verbose {0,1,2}  0 -- Doesn't print anything, 1 -- Prints number of
                     converted files, 2 -- Prints number of converted files
                     and unconverted files path.
```

## Questions and Issues

For questions and issues please use this repo's Issue tracker on Github.


<!-- ## References -->

