parsers = {}


def get_team_metadata(*args, **kwargs):
    return {"event_name": "get_team_metadata", "properties": {}}


parsers['get_team_metadata'] = get_team_metadata


def invite_contributor_to_team(*args, **kwargs):
    admin = args[1:2]
    if admin:
        admin = "CUSTOM"
    else:
        admin = "DEFAULT"

    return {
        "event_name": "invite_contributor_to_team",
        "properties": {
            "Admin": admin
        }
    }


parsers['invite_contributor_to_team'] = invite_contributor_to_team


def delete_contributor_to_team_invitation(*args, **kwargs):
    return {
        "event_name": "delete_contributor_to_team_invitation",
        "properties": {}
    }


parsers['delete_contributor_to_team_invitation'
       ] = delete_contributor_to_team_invitation


def search_team_contributors(*args, **kwargs):
    return {
        "event_name": "search_team_contributors",
        "properties":
            {
                "Email": bool(args[0:1]),
                "Name": bool(args[1:2]),
                "Surname": bool(args[2:3])
            }
    }


parsers['search_team_contributors'] = search_team_contributors


def search_projects(*args, **kwargs):
    return {
        "event_name": "search_projects",
        "properties": {
            "Metadata": bool(args[2:3])
        }
    }


parsers['search_projects'] = search_projects


def create_project(*args, **kwargs):
    return {
        "event_name": "create_project",
        "properties": {
            "Project Type": args[2:3][0]
        }
    }


parsers['create_project'] = create_project


def create_project_from_metadata(*args, **kwargs):
    return {"event_name": "create_project_from_metadata", "properties": {}}


parsers['create_project_from_metadata'] = create_project_from_metadata


def clone_project(*args, **kwargs):
    return {
        "event_name": "clone_project",
        "properties":
            {
                "Copy Classes": bool(args[3:4]),
                "Copy Settings": bool(args[4:5]),
                "Copy Workflow": bool(args[5:6]),
                "Copy Contributors": bool(args[6:7])
            }
    }


parsers['clone_project'] = clone_project


def search_images(*args, **kwargs):
    return {
        "event_name": "search_images",
        "properties":
            {
                "Annotation Status": bool(args[2:3]),
                "Metadata": bool(args[3:4]),
            }
    }


parsers['search_images'] = search_images


def upload_images_to_project(*args, **kwargs):
    return {
        "event_name": "upload_images_to_project",
        "properties":
            {
                "Image Count": len(args[1]),
                "Annotation Status": bool(args[2:3]),
                "From S3": bool(args[3:4])
            }
    }


parsers['upload_images_to_project'] = upload_images_to_project
