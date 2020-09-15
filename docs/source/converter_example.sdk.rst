.. _ref_examples:

Annotation Format Converter Examples
==========================================

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



