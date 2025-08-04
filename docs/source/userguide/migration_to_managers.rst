=======================
Migration to Managers
=======================

This guide helps you migrate from direct SAClient methods to the new manager-based interface.

Why Migrate?
============

While direct methods continue to work, the manager interface provides:

* **Better Organization** - Related methods grouped together
* **Improved Discoverability** - Easier to find relevant functionality
* **Cleaner Code** - More intuitive API structure
* **Better IDE Support** - Enhanced autocompletion and documentation

Migration is Optional
=====================

**Important**: You don't need to migrate existing code. All direct methods continue to work exactly as before. This guide is for those who want to adopt the new manager interface.

Quick Reference
===============

Here's a quick mapping of common methods:

Projects
--------

.. code-block:: python

    # Before
    client.create_project(name, desc, type)
    client.search_projects(name="test")
    client.clone_project(new_name, from_project)
    client.delete_project(project)
    client.rename_project(project, new_name)

    # After
    client.projects.create(name, desc, type)
    client.projects.list(name="test")
    client.projects.clone(new_name, from_project)
    client.projects.delete(project)
    client.projects.rename(project, new_name)

Items
-----

.. code-block:: python

    # Before
    client.list_items(project, folder="test")
    client.attach_items(project, attachments)
    client.delete_items(project, items)
    
    # After
    client.items.list(project, folder="test")
    client.items.attach(project, attachments)
    client.delete_items(project, items)  # No manager equivalent yet

Annotations
-----------

.. code-block:: python

    # Before
    client.upload_annotations(project, annotations)
    client.get_annotations(project, items)
    client.download_annotations(project, folder)
    
    # After
    client.annotations.upload(project, annotations)
    client.annotations.get(project, items)
    client.download_annotations(project, folder)  # No manager equivalent yet

Users
-----

.. code-block:: python

    # Before
    client.list_users(project="test")
    client.get_user_metadata(email)
    client.invite_contributors_to_team(emails)
    client.add_contributors_to_project(project, emails, role)
    client.search_team_contributors(email="test")

    # After
    client.users.list(project="test")
    client.users.get_metadata(email)
    client.users.invite_to_team(emails)
    client.users.add_to_project(project, emails, role)
    client.users.search_team_contributors(email="test")

Folders
-------

.. code-block:: python

    # Before
    client.create_folder(project, folder_name)
    client.search_folders(project, name="test")
    
    # After
    client.folders.create(project, folder_name)
    client.search_folders(project, name="test")  # No manager equivalent yet

Step-by-Step Migration
======================

Step 1: Identify Manager Categories
-----------------------------------

Group your existing code by functionality:

.. code-block:: python

    # Project operations
    project = client.create_project("Test", "Description", "Vector")
    projects = client.search_projects(name="Test")
    
    # Item operations  
    items = client.list_items("Test Project")
    client.attach_items("Test Project", attachments)
    
    # User operations
    users = client.list_users(project="Test Project")
    user = client.get_user_metadata("user@example.com")

Step 2: Replace Method Calls
----------------------------

Update the method calls to use managers:

.. code-block:: python

    # Project operations → client.projects
    project = client.projects.create("Test", "Description", "Vector")
    projects = client.projects.list(name="Test")
    
    # Item operations → client.items
    items = client.items.list("Test Project")
    client.items.attach("Test Project", attachments)
    
    # User operations → client.users
    users = client.users.list(project="Test Project")
    user = client.users.get_metadata("user@example.com")

Step 3: Test Thoroughly
-----------------------

Since the underlying implementation is identical, behavior should be the same, but always test:

.. code-block:: python

    # Test that results are identical
    old_result = client.list_items("Test Project")
    new_result = client.items.list("Test Project")
    assert old_result == new_result

Common Migration Patterns
=========================

Pattern 1: Project Workflow
---------------------------

.. code-block:: python

    # Before
    def setup_project(client, name, description):
        project = client.create_project(name, description, "Vector")
        client.create_folder(name, "training")
        client.create_folder(name, "validation")
        return project
    
    # After
    def setup_project(client, name, description):
        project = client.projects.create(name, description, "Vector")
        client.folders.create(name, "training")
        client.folders.create(name, "validation")
        return project

Pattern 2: Data Processing Pipeline
-----------------------------------

.. code-block:: python

    # Before
    def process_annotations(client, project_name):
        items = client.list_items(project_name, annotation_status="Completed")
        annotations = client.get_annotations(project_name, [item["name"] for item in items])
        return annotations
    
    # After
    def process_annotations(client, project_name):
        items = client.items.list(project_name, annotation_status="Completed")
        annotations = client.annotations.get(project_name, [item["name"] for item in items])
        return annotations

Pattern 3: User Management
--------------------------

.. code-block:: python

    # Before
    def get_project_contributors(client, project_name):
        users = client.list_users(project=project_name)
        return [client.get_user_metadata(user["email"]) for user in users]
    
    # After
    def get_project_contributors(client, project_name):
        users = client.users.list(project=project_name)
        return [client.users.get_metadata(user["email"]) for user in users]

Gradual Migration Strategy
==========================

You don't need to migrate everything at once. Consider this approach:

Phase 1: New Code Only
----------------------

Use managers for all new code while leaving existing code unchanged:

.. code-block:: python

    # Existing code - leave as is
    def legacy_function(client):
        return client.create_project("Old Project", "Description", "Vector")
    
    # New code - use managers
    def new_function(client):
        return client.projects.create("New Project", "Description", "Vector")

Phase 2: Module by Module
-------------------------

Migrate one module or file at a time:

.. code-block:: python

    # project_utils.py - migrated
    def create_training_project(client, name):
        project = client.projects.create(name, "Training project", "Vector")
        client.folders.create(name, "images")
        return project
    
    # annotation_utils.py - not yet migrated
    def upload_training_data(client, project, annotations):
        return client.upload_annotations(project, annotations)

Phase 3: Complete Migration
---------------------------

Eventually migrate all code for consistency:

.. code-block:: python

    # All code now uses managers consistently
    def create_and_populate_project(client, name, attachments, annotations):
        project = client.projects.create(name, "Auto-generated", "Vector")
        client.items.attach(name, attachments)
        client.annotations.upload(name, annotations)
        return project

Best Practices for Migration
============================

1. **Test Equivalence**
   
   .. code-block:: python
   
       # Verify identical behavior
       old_result = client.list_items("Test")
       new_result = client.items.list("Test")
       assert old_result == new_result

2. **Update Documentation**
   
   .. code-block:: python
   
       def process_project(client, project_name):
           """Process project using manager interface.
           
           Args:
               client: SAClient instance
               project_name: Name of the project
               
           Returns:
               List of processed items
           """
           return client.items.list(project_name, annotation_status="Completed")

3. **Use Consistent Style**
   
   .. code-block:: python
   
       # Good: Consistent manager usage
       project = client.projects.create(...)
       items = client.items.list(...)
       users = client.users.list(...)
       
       # Avoid: Mixing styles in same function
       project = client.projects.create(...)
       items = client.list_items(...)  # inconsistent

4. **Handle Errors Consistently**
   
   .. code-block:: python
   
       try:
           project = client.projects.create("Test", "Description", "Vector")
           items = client.items.list("Test")
       except Exception as e:
           logger.error(f"Failed to setup project: {e}")

Troubleshooting
===============

Method Not Available in Manager
-------------------------------

Some methods may not yet have manager equivalents. Continue using direct methods:

.. code-block:: python

    # Use manager when available
    project = client.projects.create("Test", "Description", "Vector")
    
    # Use direct method when manager equivalent doesn't exist
    client.set_project_status("Test", "InProgress")

Import Errors
-------------

Make sure you're importing from the correct location:

.. code-block:: python

    # Correct
    from superannotate import SAClient
    client = SAClient()
    client.projects.create(...)
    
    # Incorrect - managers are not separate imports
    # from superannotate import ProjectsManager  # This won't work

Performance Considerations
==========================

Managers have identical performance to direct methods since they use the same underlying implementation:

.. code-block:: python

    import time
    
    # Both approaches have identical performance
    start = time.time()
    result1 = client.list_items("Test Project")
    time1 = time.time() - start
    
    start = time.time()
    result2 = client.items.list("Test Project")
    time2 = time.time() - start
    
    # time1 ≈ time2

Conclusion
==========

Migration to managers is optional but recommended for new projects. The manager interface provides better organization and discoverability while maintaining full backward compatibility with existing code.

Key takeaways:

* **No breaking changes** - existing code continues to work
* **Gradual migration** - migrate at your own pace
* **Identical functionality** - same features, better organization
* **Better developer experience** - improved IDE support and code organization
