=========
Utilities
=========


Compatibility with multimodal projects
--------------------------------------

.. csv-table:: Support for CSV, JSON, JSONL formats
   :file: SDK_Functions_sheet.csv
   :widths: 20, 2, 15, 10, 10, 10, 25
   :header-rows: 1

Converting annotation format
----------------------------


After exporting project annotations (in SuperAnnotate format), it is possible
to convert them to other annotation formats:

.. code-block:: python

    sa.export_annotation("<input_folder>", "<output_folder>", "<dataset_format>", "<dataset_name>",
    "<project_type>", "<task>")

.. note::

  Right now we support only SuperAnnotate annotation format to COCO annotation format conversion, but you can convert from "COCO", "Pascal VOC", "DataLoop", "LabelBox", "SageMaker", "Supervisely", "VGG", "VoTT" or "YOLO" annotation formats to SuperAnnotate annotation format.

.. _git_repo: https://github.com/superannotateai/superannotate-python-sdk

You can find more information annotation format conversion :ref:`here <ref_converter>`. We provide some examples in our `GitHub repository <git_repo_>`_. In the root folder of our github repository, you can run following commands to do conversions.

.. code-block:: python

   from superannotate import export_annotation
   from superannotate import import_annotation

    # From SA format to COCO panoptic format
    export_annotation(
       "tests/converter_test/COCO/input/fromSuperAnnotate/cats_dogs_panoptic_segm",
       "tests/converter_test/COCO/output/panoptic",
       "COCO", "panoptic_test", "Pixel","panoptic_segmentation"
    )

    # From COCO keypoints detection format to SA annotation format
    import_annotation(
       "tests/converter_test/COCO/input/toSuperAnnotate/keypoint_detection",
       "tests/converter_test/COCO/output/keypoints",
       "COCO", "person_keypoints_test", "Vector", "keypoint_detection"
    )

    # Pascal VOC annotation format to SA annotation format
    import_annotation(
       "tests/converter_test/VOC/input/fromPascalVOCToSuperAnnotate/VOC2012",
       "tests/converter_test/VOC/output/instances",
       "VOC", "instances_test", "Pixel", "instance_segmentation"
    )

    # YOLO annotation format to SA annotation format
    import_annotation(
      'tests/converter_test/YOLO/input/toSuperAnnotate',
      'tests/converter_test/YOLO/output',
      'YOLO', '', 'Vector', 'object_detection'
      )

    # LabelBox annotation format to SA annotation format
    import_annotation(
       "tests/converter_test/LabelBox/input/toSuperAnnotate/",
       "tests/converter_test/LabelBox/output/objects/",
       "LabelBox", "labelbox_example", "Vector", "object_detection"
    )

    # Supervisely annotation format to SA annotation format
    import_annotation(
       "tests/converter_test/Supervisely/input/toSuperAnnotate",
       "tests/converter_test/Supervisely/output",
       "Supervisely", "", "Vector", "vector_annotation"
    )

    # DataLoop annotation format to SA annotation format
    import_annotation(
       "tests/converter_test/DataLoop/input/toSuperAnnotate",
       "tests/converter_test/DataLoop/output",
       "DataLoop", "", "Vector", "vector_annotation"
    )

    # VGG annotation format to SA annotation format
    import_annotation(
       "tests/converter_test/VGG/input/toSuperAnnotate",
       "tests/converter_test/VGG/output",
       "VGG", "vgg_test", "Vector", "instance_segmentation"
    )

    # VoTT annotation format to SA annotation format
    import_annotation(
       "tests/converter_test/VoTT/input/toSuperAnnotate",
       "tests/converter_test/VoTT/output",
       "VoTT", "", "Vector", "vector_annotation"
    )

    # GoogleCloud annotation format to SA annotation format
    import_annotation(
       "tests/converter_test/GoogleCloud/input/toSuperAnnotate",
       "tests/converter_test/GoogleCloud/output",
       "GoogleCloud", "image_object_detection", "Vector", "object_detection"
    )

    # GoogleCloud annotation format to SA annotation format
    import_annotation(
       "tests/converter_test/SageMaker/input/toSuperAnnotate",
       "tests/converter_test/SageMaker/output",
       "SageMaker", "test-obj-detect", "Vector", "object_detection"
    )


pandas DataFrame out of project annotations and annotation instance filtering
-----------------------------------------------------------------------------


To create a `pandas DataFrame <https://pandas.pydata.org/>`_ from project
SuperAnnotate format annotations:

.. code-block:: python

   df = sa.aggregate_annotations_as_df("<path_to_project_folder>")

The created DataFrame will have columns specified at
:ref:`aggregate_annotations_as_df <ref_aggregate_annotations_as_df>`.

Example of created DataFrame:

.. image:: images/pandas_df.png

Each row represents annotation information. One full annotation with multiple
attribute groups can be grouped under :code:`instanceId` field.
