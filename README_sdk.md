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

## Get the team you want to work with

First you need the get the team to work with:

    team = sa.get_default_team()

You can also search for the team with:

    teams = sa.search_teams(name_prefix="my first team")

All the SDK search functions are with name prefix and are case insensitive.
You probably have only one team with prefix "my first team", so it can be chosen
with 

    team = teams[0]

## Accessing projects

To access list of projects of that team with name prefix "Example Project 1":

    projects = sa.search_projects(team, "Example Project 1")

Again you probably have only one project that name prefix, so you can go ahead and
chose it with:

    project = project[0]

To upload images from folder to that project:

    sa.upload_images_from_folder(project, <path_to_my_images_folder>)
