=========================
Remote metadata reference
=========================


Projects metadata
_________________

.. _ref_metadata:

Project metadata example:

.. code-block:: python

   {
     "name": "Example Project test",
     "description": "test vector",
     "creator_id": "admin@superannotate.com",
     "updatedAt": "2020-08-31T05:43:43.118Z",
     "createdAt": "2020-08-31T05:43:43.118Z"
     "type": "Vector",
     "attachment_name": None,
     "attachment_path": None,
     "entropy_status": 1,
     "status": "NotStarted",
     "item_count": 123,
     "...": "..."
   }


----------

Setting metadata
_________________

Setting metadata example:

.. code-block:: python

   {
    "attribute": "FrameRate",
    "value": 3
   }


----------

Export metadata
_______________

Export metadata example:

.. code-block:: python

   {
     "name": "Aug 17 2020 15:44 First Name.zip",
     "user_id": "user@gmail.com",
     "status": 2,
     "createdAt": "2020-08-17T11:44:26.000Z",
     "...": "..."
   }


----------


Integration metadata
______________________

Integration metadata example:

.. code-block:: python

   {
   "name": "My S3 Bucket",
   "type": "aws",
   "root": "test-openseadragon-1212"
    }


----------


Item metadata
_______________

Item metadata example:

.. code-block:: python

  {
   "name": "example.jpeg",
   "path": "project/folder_1/meow.jpeg",
   "url": "https://sa-public-files.s3.../text_file_example_1.jpeg",
   "annotation_status": "NotStarted",
   "annotator_name": None,
   "qa_name": None,
   "entropy_value": None,
   "createdAt": "2022-02-15T20:46:44.000Z",
   "updatedAt": "2022-02-15T20:46:44.000Z"
    }

----------


Image metadata
_______________


Image metadata example:

.. code-block:: python

   {
      "name": "000000000001.jpg",
      "annotation_status": "Completed",
      "prediction_status": "NotStarted",
      "segmentation_status": "NotStarted",
      "annotator_id": None,
      "annotator_name": None,
      "qa_id": None,
      "qa_name": None,
      "entropy_value": None,
      "approval_status": None,
      "createdAt": "2020-08-18T07:30:06.000Z",
      "updatedAt": "2020-08-18T07:30:06.000Z"
      "is_pinned": 0,
      "...": "...",
   }


----------

Priority score
_______________


Priority score example:

.. code-block:: python

   {
        "name" : "image1.png",
        "priority": 0.567
    }


----------

Attachment
_______________


Attachment example:

.. code-block:: python

   {
      "url": "https://sa-public-files.s3.../text_file_example_1.jpeg",
      "name": "example.jpeg"
   }


----------

.. _ref_class:

Annotation class metadata
_________________________


Annotation class metadata example:

.. code-block:: python

  {
    "id": 4444,
    "name": "Human",
    "color": "#e4542b",
    "attribute_groups": [
       {
          "name": "tall",
          "attributes": [
             {
                "name": "yes"
             },
             {
                "name": "no"
             }
          ]
       },
       {
         "name": "age",
         "attributes": [
             {
               "name": "young"
             },
             {
               "name": "old"
             }
         ]
       }
    ],

    "...": "..."
  }



----------

Team contributor metadata
_________________________

Team contributor metadata example:

.. code-block:: python

  {
    "id": "admin@superannotate.com",
    "first_name": "First Name",
    "last_name": "Last Name",
    "email": "admin@superannotate.com",
    "user_role": 6
    "...": "...",
  }
