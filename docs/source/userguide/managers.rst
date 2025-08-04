================
Using Managers
================

The SuperAnnotate Python SDK provides a manager-based interface that organizes functionality into logical groups. This guide explains how to use managers effectively.

What are Managers?
==================

Managers are specialized classes that group related functionality together. Instead of having all methods directly on the SAClient, managers organize methods by domain:

* **Projects Manager** (``client.projects``) - Project operations
* **Folders Manager** (``client.folders``) - Folder operations  
* **Items Manager** (``client.items``) - Item operations
* **Annotations Manager** (``client.annotations``) - Annotation operations
* **Users Manager** (``client.users``) - User operations

Why Use Managers?
=================

**Better Organization**
  Related methods are grouped together, making the API easier to navigate and understand.

**Cleaner Interface**
  Instead of searching through dozens of methods on SAClient, you can focus on the specific domain you're working with.

**Backward Compatibility**
  All existing SAClient methods continue to work exactly as before.

**Discoverability**
  IDE autocompletion works better when methods are organized by domain.

Getting Started
===============

Basic Usage
-----------

.. code-block:: python

    from superannotate import SAClient
    
    client = SAClient()
    
    # Access managers through the client
    projects_manager = client.projects
    items_manager = client.items
    users_manager = client.users

Manager vs Direct Methods
-------------------------

You can use either approach - they're functionally equivalent:

.. code-block:: python

    # Using managers (recommended)
    project = client.projects.create("My Project", "Description", "Vector")
    items = client.items.list("My Project")
    
    # Using direct methods (still supported)
    project = client.create_project("My Project", "Description", "Vector")
    items = client.list_items("My Project")

Projects Manager
================

The Projects Manager handles all project-related operations.

Creating Projects
-----------------

.. code-block:: python

    # Create a basic project
    project = client.projects.create(
        project_name="Medical Imaging",
        project_description="Medical image annotation project",
        project_type="Vector"
    )
    
    # Create a project with settings and classes
    project = client.projects.create(
        project_name="Advanced Project",
        project_description="Project with custom settings",
        project_type="Pixel",
        settings=[
            {"attribute": "image_quality", "value": "original"}
        ],
        classes=[
            {"name": "tumor", "color": "#FF0000", "type": "bbox"}
        ]
    )

Listing Projects
----------------

.. code-block:: python

    # List by name
    projects = client.projects.list(name="Medical")

    # Get project metadata
    projects = client.projects.list(
        name="Medical",
        return_metadata=True,
        status="InProgress"
    )

    # Get all projects
    all_projects = client.projects.list()

Cloning Projects
----------------

.. code-block:: python

    # Clone a project with all settings
    cloned_project = client.projects.clone(
        project_name="Medical Imaging Copy",
        from_project="Medical Imaging",
        copy_annotation_classes=True,
        copy_settings=True,
        copy_contributors=True
    )

Managing Projects
-----------------

.. code-block:: python

    # Delete a project
    client.projects.delete("Old Project")

    # Rename a project
    client.projects.rename("Old Name", "New Name")

Items Manager
=============

The Items Manager handles item-related operations like listing, attaching, and managing items.

Listing Items
-------------

.. code-block:: python

    # List all items in a project
    items = client.items.list("My Project")
    
    # List items in a specific folder
    items = client.items.list("My Project", folder="subfolder")
    
    # List items with filtering
    items = client.items.list(
        project="My Project",
        annotation_status="InProgress",
        name__contains="scan"
    )
    
    # Include custom metadata
    items = client.items.list(
        project="My Project",
        include=["custom_metadata"]
    )

Attaching Items
---------------

.. code-block:: python

    # Attach items from URLs
    uploaded, failed, duplicated = client.items.attach(
        project="My Project",
        attachments=[
            {"name": "image1.jpg", "url": "https://example.com/image1.jpg"},
            {"name": "image2.jpg", "url": "https://example.com/image2.jpg"}
        ]
    )
    
    # Attach items from CSV file
    uploaded, failed, duplicated = client.items.attach(
        project="My Project",
        attachments="path/to/attachments.csv"
    )

Annotations Manager
===================

The Annotations Manager handles uploading, downloading, and managing annotations.

Uploading Annotations
---------------------

.. code-block:: python

    # Upload annotations
    result = client.annotations.upload(
        project="My Project/folder",
        annotations=[
            {
                "metadata": {"name": "image1.jpg"},
                "instances": [
                    {
                        "type": "bbox",
                        "className": "person",
                        "points": {"x1": 100, "y1": 100, "x2": 200, "y2": 200}
                    }
                ]
            }
        ]
    )
    
    # Upload for multimodal projects
    result = client.annotations.upload(
        project="My Multimodal Project",
        annotations=annotations_list,
        data_spec="multimodal"
    )

Getting Annotations
-------------------

.. code-block:: python

    # Get annotations for specific items
    annotations = client.annotations.get(
        project="My Project",
        items=["image1.jpg", "image2.jpg"]
    )
    
    # Get annotations for multimodal projects
    annotations = client.annotations.get(
        project="My Multimodal Project",
        items=["item1", "item2"],
        data_spec="multimodal"
    )

Users Manager
=============

The Users Manager handles user-related operations like listing users and managing permissions.

Listing Users
-------------

.. code-block:: python

    # List all team users
    users = client.users.list()
    
    # List project users
    users = client.users.list(project="My Project")
    
    # List users with custom fields
    users = client.users.list(
        include=["custom_fields"],
        role="Annotator"
    )
    
    # Filter users
    users = client.users.list(
        email__contains="@company.com",
        state="Confirmed"
    )

Getting User Metadata
---------------------

.. code-block:: python

    # Get user by email
    user = client.users.get_metadata("user@example.com")
    
    # Get user with custom fields
    user = client.users.get_metadata(
        "user@example.com",
        include=["custom_fields"]
    )

Managing Contributors
---------------------

.. code-block:: python

    # Invite users to team
    invited, skipped = client.users.invite_to_team(
        emails=["user1@example.com", "user2@example.com"],
        admin=False
    )

    # Add contributors to project
    added, skipped = client.users.add_to_project(
        project="My Project",
        emails=["annotator@example.com"],
        role="Annotator"
    )

    # Search team contributors
    contributors = client.users.search_team_contributors(
        email="@company.com",
        return_metadata=True
    )

Folders Manager
===============

The Folders Manager handles folder operations within projects.

Creating Folders
----------------

.. code-block:: python

    # Create a folder in a project
    folder = client.folders.create("My Project", "new_folder")

Best Practices
==============

Consistent Usage
----------------

Choose one approach and stick with it throughout your codebase:

.. code-block:: python

    # Good: Consistent manager usage
    client.projects.create(...)
    client.items.list(...)
    client.annotations.upload(...)
    
    # Good: Consistent direct method usage
    client.create_project(...)
    client.list_items(...)
    client.upload_annotations(...)
    
    # Avoid: Mixing approaches unnecessarily
    client.projects.create(...)
    client.list_items(...)  # inconsistent

Error Handling
--------------

Error handling works the same way with managers:

.. code-block:: python

    try:
        project = client.projects.create("My Project", "Description", "Vector")
        items = client.items.list("My Project")
    except Exception as e:
        print(f"Error: {e}")

IDE Support
-----------

Managers provide better IDE autocompletion and documentation:

.. code-block:: python

    # Type 'client.projects.' and your IDE will show:
    # - create()
    # - search()
    # - clone()
    
    # Type 'client.items.' and your IDE will show:
    # - list()
    # - attach()

Migration Guide
===============

If you have existing code using direct SAClient methods, you don't need to change anything. However, if you want to migrate to managers:

**Step 1: Identify the domain**

.. code-block:: python

    # Project operations → client.projects
    client.create_project(...) → client.projects.create(...)
    client.search_projects(...) → client.projects.search(...)
    
    # Item operations → client.items  
    client.list_items(...) → client.items.list(...)
    client.attach_items(...) → client.items.attach(...)
    
    # User operations → client.users
    client.list_users(...) → client.users.list(...)
    client.get_user_metadata(...) → client.users.get_metadata(...)

**Step 2: Update method calls**

The parameters remain exactly the same, just the calling pattern changes:

.. code-block:: python

    # Before
    items = client.list_items(
        project="My Project",
        folder="subfolder",
        annotation_status="InProgress"
    )
    
    # After
    items = client.items.list(
        project="My Project", 
        folder="subfolder",
        annotation_status="InProgress"
    )

**Step 3: Test thoroughly**

Since the underlying implementation is the same, behavior should be identical, but always test your changes.
