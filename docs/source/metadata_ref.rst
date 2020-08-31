.. _ref_metadata:

SDK Metadata Reference
===========================

.. contents::

----------

Projects metadata
_________________

Project metadata example:

.. code-block:: python

   {
     "name": "Example Project test",
     "description": "test vector",
     "creator_id": "hovnatan@superannotate.com",
     "updatedAt": "2020-08-31T05:43:43.118Z",
     "createdAt": "2020-08-31T05:43:43.118Z"
     "type": 1,
     "attachment_name": None,
     "attachment_path": None,
     "entropy_status": 1,
     "status": 0,
     "id": 1111,
     "team_id": 2222,
     "...": "..."
   }


----------

Export metadata
_______________

Export metadata example:

.. code-block:: python

   {
     "name": "Aug 17 2020 15:44 Hovnatan.zip",
     "user_id": "hovnatan@gmail.com",
     "status": 2,
     "createdAt": "2020-08-17T11:44:26.000Z",
     "...": "..."
   }


----------

Image metadata
_______________


Image metadata example:

.. code-block:: python

   {
     "name": "000000000001.jpg",
     "annotation_status": 1,
     "prediction_status": 1,
     "segmentation_status": 1,
     "annotator_id": None,
     "annotator_name": None,
     "qa_id": None,
     "qa_name": None,
     "entropy_value": None,
     "approval_status": None,
     "createdAt": "2020-08-18T07:30:06.000Z",
     "updatedAt": "2020-08-18T07:30:06.000Z"
     "project_id": 2734,
     "id": 523862,
     "is_pinned": 0,
     "team_id": 315,
     "...": "...",
 }


----------

Annotation class metadata
_________________________

Annotation class metadata example:

.. code-block:: python

  {
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

User metadata
_________________________

User metadata example:

.. code-block:: python

  {
    "id": "hovnatan@superannotate.com",
    "first_name": "Hovnatan",
    "last_name": "Karapetyan",
    "email": "hovnatan@superannotate.com",
    "user_role": 6
    "...": "...",
  }

