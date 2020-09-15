.. _ref_examples:

SDK Annotation Format Converters Examples
==========================================

Argument detailed description:
_______________________________

SuperAnnotate has two possible project types 'Vector' or 'Pixel'.

'Vector' project creates [IMAGE_NAME]___objects.json for each image. 

'Pixel' project creates [IMAGE_NAME]___pixel.jsons and [IMAGE_NAME]___save.png annotation mask for each image. 


Datasets can be used for different tasks, we choose tasks from COCO dataset. Possible candidates are:'panoptic_segmentation', 'instance_segmentation', 'keypoint_detection' and 'object_detection'.

'keypoint_detection' can be used to converts keypoints from/to available annotation format.

'panoptic_segmentation' will use panoptic mask for each image to generate bluemask for SuperAnnotate annotation format and use bluemask to generate panoptic mask for invert conversion. Panoptic masks should be in the input folder. 

'instance_segmentation' 'Pixel' project_type converts instance masks and 'Vector' project_type generates bounding boxes and polygons from instance masks. Masks should be in the input folder if it is 'Pixel' project_type. 

'object_detection' converts objects from/to available annotation format


Those two arguments in the conversion functions describe the flow of converters. As some datasets don't have all possible tasks or for all possible tasks not all SuperAnnotate projects are possible, bellow we will present which (project_type, task) combinations are available:

==============  ======================
         From SA to COCO
--------------------------------------
 project type           task
==============  ======================
Pixel           panoptic_segmentation
Pixel           instance_segmentation
Vector          instance_segmentation
Vector			 object_detection
Vector			 keypoint_detection
==============  ====================== 

==============  ======================
         From COCO to SA
--------------------------------------
 project type           task
==============  ======================
Pixel           panoptic_segmentation
Vector          instance_segmentation
Vector			 keypoint_detection
==============  ====================== 

==============  ======================
         From VOC to SA
--------------------------------------
 project type           task
==============  ======================
Pixel           instance_segmentation
Vector			object_detection
==============  ====================== 

==============  ======================
       From LabelBox to SA
--------------------------------------
 project type           task
==============  ======================
Vector			object_detection
==============  ====================== 

Examples
_________

We provide some examples in our github repository. In the root folder of our github repository, you can run following commands to do conversions.

Example 1: Convert SuperAnnotate panoptic format to COCO panoptic format

.. code-block:: python

   import superannotate as sa
   sa.export_annotation_format("tests/converter_test/COCO/input/fromSuperAnnotate/cats_dogs_panoptic_segm", "tests/converter_test/COCO/output/panoptic","COCO","panoptic_test", "Pixel","panoptic_segmentation","Web")

Example 2: Convert from COCO keypoints detection format to SuperAnnotate keypoints detection desktop application format with two lines:


.. code-block:: python

   import superannotate as sa
   sa.import_annotation_format("tests/converter_test/COCO/input/toSuperAnnotate/keypoint_detection", "tests/converter_test/COCO/output/keypoints", "COCO", "person_keypoints_test", "Vector", "keypoint_detection", "Desktop")

Example 3: Convert from Pascal VOC annotation format to SuperAnnotate Web platform annotation format:

.. code-block:: python

   import superannotate as sa
   sa.import_annotation_format("tests/converter_test/VOC/input/fromPascalVOCToSuperAnnotate/VOC2012", "tests/converter_test/VOC/output/instances", "VOC", "instances_test", "Pixel", "instance_segmentation", "Web")

Example 4: Convert from LabelBox annotation format to SuperAnnotate Desktop application annotation format:

.. code-block:: python

	import superannotate as sa
	sa.import_annotation_format("tests/converter_test/LabelBox/input/toSuperAnnotate/", "tests/converter_test/LabelBox/output/objects/", "LabelBox", "labelbox_example", "Vector", "object_detection", "Desktop")



