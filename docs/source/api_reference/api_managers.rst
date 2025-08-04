========
Managers
========

The SAClient provides manager interfaces for organized access to different resource types. 
Managers group related functionality together and provide a cleaner, more intuitive API structure.

Overview
========

The manager pattern organizes SAClient functionality into domain-specific managers:

* **Projects Manager** - Handle project operations (create, search, clone, etc.)
* **Folders Manager** - Handle folder operations (create, list, delete, etc.)
* **Items Manager** - Handle item operations (list, attach, delete, etc.)
* **Annotations Manager** - Handle annotation operations (upload, get, delete, etc.)
* **Users Manager** - Handle user operations (list, get metadata, manage permissions, etc.)

Usage
=====

You can access managers through the SAClient instance:

.. code-block:: python

    from superannotate import SAClient
    
    client = SAClient()
    
    # Using managers
    project = client.projects.create("My Project", "Description", "Vector")
    items = client.items.list("My Project")
    users = client.users.list(project="My Project")
    
    # Traditional methods still work for backward compatibility
    project = client.create_project("My Project", "Description", "Vector")
    items = client.list_items("My Project")
    users = client.list_users(project="My Project")

Benefits
========

* **Better Organization** - Related methods are grouped together
* **Cleaner Interface** - Easier to discover and use related functionality
* **Backward Compatibility** - Existing code continues to work unchanged
* **Extensibility** - Easy to add new methods to specific domains

Projects Manager
================

.. autoclass:: superannotate.lib.app.interface.sdk_interface.ProjectsManager
    :members:
    :undoc-members:
    :show-inheritance:

**Available Methods:**

* ``create(project_name, project_description, project_type, ...)`` - Create a new project
* ``list(name, return_metadata, include_complete_item_count, status)`` - List/search for projects
* ``clone(project_name, from_project, ...)`` - Clone an existing project
* ``delete(project)`` - Delete a project
* ``rename(project, new_name)`` - Rename a project

Folders Manager
===============

.. autoclass:: superannotate.lib.app.interface.sdk_interface.FoldersManager
    :members:
    :undoc-members:
    :show-inheritance:

**Available Methods:**

* ``create(project, folder_name)`` - Create a new folder in a project

Items Manager
=============

.. autoclass:: superannotate.lib.app.interface.sdk_interface.ItemsManager
    :members:
    :undoc-members:
    :show-inheritance:

**Available Methods:**

* ``list(project, folder, include, **filters)`` - List items with filtering
* ``attach(project, attachments, annotation_status)`` - Attach items to a project

Annotations Manager
===================

.. autoclass:: superannotate.lib.app.interface.sdk_interface.AnnotationsManager
    :members:
    :undoc-members:
    :show-inheritance:

**Available Methods:**

* ``upload(project, annotations, keep_status, data_spec)`` - Upload annotations
* ``get(project, items, data_spec)`` - Get annotations for items

Users Manager
=============

.. autoclass:: superannotate.lib.app.interface.sdk_interface.UsersManager
    :members:
    :undoc-members:
    :show-inheritance:

**Available Methods:**

* ``list(project, include, **filters)`` - List users with filtering
* ``get_metadata(pk, include)`` - Get user metadata
* ``invite_to_team(emails, admin)`` - Invite contributors to team
* ``add_to_project(project, emails, role)`` - Add contributors to project
* ``search_team_contributors(email, first_name, last_name, return_metadata)`` - Search team contributors

Migration Guide
===============

Existing code using direct SAClient methods will continue to work without changes. 
However, you can gradually migrate to the manager interface for better organization:

**Before (still works):**

.. code-block:: python

    client = SAClient()
    
    # Direct methods
    project = client.create_project("My Project", "Description", "Vector")
    items = client.list_items("My Project")
    annotations = client.get_annotations("My Project", ["item1.jpg"])
    users = client.list_users(project="My Project")

**After (recommended):**

.. code-block:: python

    client = SAClient()
    
    # Using managers
    project = client.projects.create("My Project", "Description", "Vector")
    items = client.items.list("My Project")
    annotations = client.annotations.get("My Project", ["item1.jpg"])
    users = client.users.list(project="My Project")

Examples
========

Creating and Managing Projects
------------------------------

.. code-block:: python

    from superannotate import SAClient
    
    client = SAClient()
    
    # Create a new project
    project = client.projects.create(
        project_name="Medical Imaging",
        project_description="Medical image annotation project",
        project_type="Vector"
    )
    
    # List projects
    projects = client.projects.list(
        name="Medical",
        return_metadata=True,
        status="InProgress"
    )
    
    # Clone an existing project
    cloned_project = client.projects.clone(
        project_name="Medical Imaging Copy",
        from_project="Medical Imaging",
        copy_annotation_classes=True,
        copy_settings=True
    )

Working with Items
------------------

.. code-block:: python

    # List items with filtering
    items = client.items.list(
        project="Medical Imaging",
        folder="scans",
        include=["custom_metadata"],
        annotation_status="InProgress"
    )
    
    # Attach new items
    uploaded, failed, duplicated = client.items.attach(
        project="Medical Imaging",
        attachments=[
            {"name": "scan1.jpg", "url": "https://example.com/scan1.jpg"},
            {"name": "scan2.jpg", "url": "https://example.com/scan2.jpg"}
        ]
    )

Managing Annotations
--------------------

.. code-block:: python

    # Upload annotations
    result = client.annotations.upload(
        project="Medical Imaging/scans",
        annotations=[
            {
                "metadata": {"name": "scan1.jpg"},
                "instances": [
                    {"type": "bbox", "className": "tumor", "points": {...}}
                ]
            }
        ],
        data_spec="multimodal"
    )
    
    # Get annotations
    annotations = client.annotations.get(
        project="Medical Imaging/scans",
        items=["scan1.jpg", "scan2.jpg"],
        data_spec="multimodal"
    )

User Management
---------------

.. code-block:: python

    # List project users with custom fields
    users = client.users.list(
        project="Medical Imaging",
        include=["custom_fields"],
        role="Annotator"
    )
    
    # Get specific user metadata
    user = client.users.get_metadata(
        "annotator@example.com",
        include=["custom_fields"]
    )
