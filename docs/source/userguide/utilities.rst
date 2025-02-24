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


Converting CSV and JSONL Formats for Annotation Management in SuperAnnotate
---------------------------------------------------------------------------
SuperAnnotate primarily uses the **JSONL format** for annotation import/export. However,
many external tools use **CSV**, requiring users to convert between these formats for seamless data management.

This guide provides:

- CSV to JSONL conversion** for annotation uploads.
- Fetching annotations from SuperAnnotate** and converting them into JSONL/CSV.
- Correct metadata mappings** to ensure consistency in the annotation format.


SuperAnnotate JSONL Schema Overview
===================================
Before diving into conversions, here's a breakdown of SuperAnnotate's JSONL schema:

.. code-block:: json

    {
      "metadata": {
        "name": "sample_image.jpg",
        "item_category": { "value": "category1" },
        "folder_name": "dataset_folder"
      },
      "data": {
        "attribute1": { "value": "label1" },
        "attribute2": { "value": "label2" }
      }
    }

Key Fields:
    - **metadata.name** → The item's name (e.g., image file name).
    - **metadata.item_category** → Optional category assigned to the item.
    - **metadata.folder_name** → The dataset folder name (previously `_folder` in CSV).
    - **data** → Stores key-value pairs for attributes.


Converting CSV to JSONL and Uploading Annotations
=================================================

Steps to Convert CSV to JSONL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Read the **CSV file** and extract annotation fields.
2. Map metadata (`_item_name`, `_item_category`, `_folder`) to **SuperAnnotate's JSONL format**.
3. Convert remaining fields into JSONL **data attributes**.
4. Upload the JSONL file to **SuperAnnotate using SAClient**.

Example Python Script:

.. code-block:: python

    import csv
    import json
    from pathlib import Path
    from superannotate import SAClient

    def csv_to_jsonl(csv_path, jsonl_path):
        """Convert CSV annotations to JSONL format with correct mappings."""
        with open(csv_path, newline='', encoding='utf-8') as csv_file, open(jsonl_path, 'w', encoding='utf-8') as jsonl_file:
            reader = csv.DictReader(csv_file)

            for row in reader:
                jsonl_entry = {
                    "metadata": {
                        "name": row["_item_name"],
                        "item_category": {"value": row["_item_category"]},
                        "folder_name": row["_folder"]
                    },
                    "data": {}
                }

                for key, value in row.items():
                    if key not in ["_item_name", "_item_category", "_folder"]:
                        jsonl_entry["data"][key] = {"value": json.loads(value)}

                json.dump(jsonl_entry, jsonl_file)
                jsonl_file.write('\n')

    # Convert CSV to JSONL
    csv_to_jsonl("annotations.csv", "annotations.jsonl")

    # Upload to SuperAnnotate
    sa = SAClient()
    annotations = [json.loads(line) for line in Path("annotations.jsonl").open("r", encoding="utf-8")]

    response = sa.upload_annotations(
        project="project1/folder1",
        annotations=annotations,
        keep_status=True,
        data_spec="multimodal"
    )


Fetching Annotations and Converting to JSONL/CSV
================================================

Steps to Retrieve and Convert Annotations:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Fetch **annotations from SuperAnnotate** using `sa.get_annotations()`.
2. Convert the **annotation list into JSONL format**.
3. Convert the **JSONL data into CSV** for external use.

Python Script to Convert Annotations to JSONL:

.. code-block:: python

    def convert_annotations_to_jsonl(annotations, jsonl_path):
        """Convert SuperAnnotate annotations list to JSONL format."""
        with open(jsonl_path, 'w', encoding='utf-8') as jsonl_file:
            for annotation in annotations:
                json.dump(annotation, jsonl_file)
                jsonl_file.write('\n')

    # Fetch annotations from SuperAnnotate
    sa = SAClient()
    annotations = sa.get_annotations("project", data_spec="multimodal")

    # Convert to JSONL
    convert_annotations_to_jsonl(annotations, "fetched_annotations.jsonl")

Python Script to Convert JSONL to CSV:

.. code-block:: python

    def convert_jsonl_to_csv(jsonl_path, csv_path):
        """Convert JSONL file to CSV format with correct mappings."""
        with open(jsonl_path, 'r', encoding='utf-8') as jsonl_file, open(csv_path, 'w', newline='', encoding='utf-8') as csv_file:
            data = [json.loads(line) for line in jsonl_file]

            if not data:
                return

            # Extract field names from the first entry
            fieldnames = ["_item_name", "_item_category", "_folder"] + list(data[0]["data"].keys())

            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

            for entry in data:
                row = {
                    "_item_name": entry["metadata"]["name"],
                    "_item_category": entry["metadata"].get("item_category", {}).get("value"),
                    "_folder": entry["metadata"].get("folder_name", None)
                }

                for key in entry["data"]:
                    value = entry["data"][key]
                    row[key] = value["value"] if isinstance(value, dict) else value

                writer.writerow(row)

    # Convert JSONL to CSV
    convert_jsonl_to_csv("fetched_annotations.jsonl", "converted_annotations.csv")

Conclusion
==========
This guide provides a **seamless way to convert** annotations between CSV and JSONL formats while maintaining
compatibility with **SuperAnnotate's platform**.
By following these steps, users can efficiently **import, export, and manage annotation data** in their projects.

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
