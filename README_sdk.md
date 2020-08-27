Python SDK to [Superannotate](https://app.superannotate.com) platform


# Quick tutorial


## Installation

    pip install superannotate

## First steps

    import superannotate as sa

## Initialize and authenticate

To get the access token visit SDK token in team settings. Generate the token and copy it into a local JSON file with key "token", e.g.,

    {
        "token" : "...."
    }

    sa.init(<path_to_my_config_json>)

## Accessing projects

To access list of projects of that team with name prefix "Example Project 1":

    projects = sa.search_projects("Example Project 1")

Again you probably have only one project that name prefix, so you can go ahead and
chose it with:

    project = project[0]

To upload images from folder to that project:

    sa.upload_images_from_folder(project, <path_to_my_images_folder>)
