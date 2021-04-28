parsers = {}


def get_project_name(project):
    project_name = ""
    if isinstance(project, dict):
        project_name = project['name']
    if isinstance(project, str):
        if '/' in project:
            project_name = project.split('/')[0]
        else:
            project_name = project
    return project_name


def get_team_metadata(*args, **kwargs):
    return {"event_name": "get_team_metadata", "properties": {}}


parsers['get_team_metadata'] = get_team_metadata


def invite_contributor_to_team(*args, **kwargs):
    admin = kwargs.get("admin", None)
    if not admin:
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
                "Email": bool(args[0:1] or kwargs.get("email", None)),
                "Name": bool(args[1:2] or kwargs.get("first_name", None)),
                "Surname": bool(args[2:3] or kwargs.get("last_name", None))
            }
    }


parsers['search_team_contributors'] = search_team_contributors


def search_projects(*args, **kwargs):
    project = kwargs.get("name", None)
    if not project:
        project = args[0:1][0]
    return {
        "event_name": "search_projects",
        "properties":
            {
                "Metadata":
                    bool(args[2:3] or kwargs.get("return_metadata", None)),
                "project_name":
                    get_project_name(project)
            }
    }


parsers['search_projects'] = search_projects


def create_project(*args, **kwargs):
    project = kwargs.get("project_name", None)
    if not project:
        project = args[0:1][0]
    project_type = kwargs.get("project_type", None)
    if not project_type:
        project_type = args[2:3][0]

    return {
        "event_name": "create_project",
        "properties":
            {
                "Project Type": project_type,
                "project_name": get_project_name(project)
            }
    }


parsers['create_project'] = create_project


def create_project_from_metadata(*args, **kwargs):
    project = kwargs.get("project_metadata", None)
    if not project:
        project = args[0:1][0]
    return {
        "event_name": "create_project_from_metadata",
        "properties": {
            "project_name": get_project_name(project)
        }
    }


parsers['create_project_from_metadata'] = create_project_from_metadata


def clone_project(*args, **kwargs):
    project = kwargs.get("project_name", None)
    if not project:
        project = args[0:1][0]
    return {
        "event_name": "clone_project",
        "properties":
            {
                "Copy Classes":
                    bool(
                        args[3:4] or
                        kwargs.get("copy_annotation_classes", None)
                    ),
                "Copy Settings":
                    bool(args[4:5] or kwargs.get("copy_settings", None)),
                "Copy Workflow":
                    bool(args[5:6] or kwargs.get("copy_workflow", None)),
                "Copy Contributors":
                    bool(args[6:7] or kwargs.get("copy_contributors", None)),
                "project_name":
                    get_project_name(project)
            }
    }


parsers['clone_project'] = clone_project


def search_images(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]
    return {
        "event_name": "search_images",
        "properties":
            {
                "Annotation Status":
                    bool(args[2:3] or kwargs.get("annotation_status", None)),
                "Metadata":
                    bool(args[3:4] or kwargs.get("return_metadata", None)),
                "project_name":
                    get_project_name(project)
            }
    }


parsers['search_images'] = search_images


def upload_images_to_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    img_paths = kwargs.get("img_paths", [])
    if not img_paths:
        img_paths += args[1:2][0]
    return {
        "event_name": "upload_images_to_project",
        "properties":
            {
                "Image Count":
                    len(img_paths),
                "Annotation Status":
                    bool(args[2:3] or kwargs.get("annotation_status", None)),
                "From S3":
                    bool(args[3:4] or kwargs.get("from_s3", None)),
                "project_name":
                    get_project_name(project)
            }
    }


parsers['upload_images_to_project'] = upload_images_to_project


def upload_image_to_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]
    return {
        "event_name": "upload_image_to_project",
        "properties":
            {
                "Image Name":
                    bool(args[2:3] or kwargs.get("image_name", None)),
                "Annotation Status":
                    bool(args[3:4] or kwargs.get("annotation_status", None)),
                "project_name":
                    get_project_name(project)
            }
    }


parsers['upload_image_to_project'] = upload_image_to_project


def upload_images_from_public_urls_to_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    img_urls = kwargs.get("img_urls", [])
    if not img_urls:
        img_urls += args[1:2][0]
    return {
        "event_name": "upload_images_from_public_urls_to_project",
        "properties":
            {
                "Image Count":
                    len(img_urls),
                "Image Name":
                    bool(args[2:3] or kwargs.get("img_names", None)),
                "Annotation Status":
                    bool(args[3:4] or kwargs.get("annotation_status", None)),
                "project_name":
                    get_project_name(project)
            }
    }


parsers['upload_images_from_public_urls_to_project'
       ] = upload_images_from_public_urls_to_project


def upload_images_from_google_cloud_to_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]
    return {
        "event_name": "upload_images_from_google_cloud_to_project",
        "properties": {
            "project_name": get_project_name(project)
        }
    }


parsers['upload_images_from_google_cloud_to_project'
       ] = upload_images_from_google_cloud_to_project
