.. _sdk:

SDK functions
===========================

.. contents::


Initialization and authentication
_________________________________

.. autofunction:: superannotate.init

----------

Teams
_____

.. autofunction:: superannotate.get_default_team
.. autofunction:: superannotate.search_teams
.. autofunction:: superannotate.create_team
.. autofunction:: superannotate.delete_team

----------

Projects
________

.. autofunction:: superannotate.search_projects
.. autofunction:: superannotate.create_project
.. autofunction:: superannotate.delete_project
.. autofunction:: superannotate.get_project_image_count
.. autofunction:: superannotate.upload_images_to_project
.. autofunction:: superannotate.upload_images_from_folder_to_project
.. autofunction:: superannotate.upload_annotations_from_folder_to_project
.. autofunction:: superannotate.upload_preannotations_from_folder_to_project
.. autofunction:: superannotate.share_project
.. autofunction:: superannotate.unshare_project

----------

Project Classes
_______________

.. automodule:: superannotate.db.project_classes
   :members:
   :undoc-members:

----------

Images
______

.. automodule:: superannotate.db.images
   :members:
   :undoc-members:

----------

Exports
_______

.. automodule:: superannotate.db.exports
   :members:
   :undoc-members:

----------

Users
_____

.. automodule:: superannotate.db.users
   :members:
   :undoc-members:
