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


def upload_images_from_azure_blob_to_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]
    return {
        "event_name": "upload_images_from_azure_blob_to_project",
        "properties": {
            "project_name": get_project_name(project)
        }
    }


parsers['upload_images_from_azure_blob_to_project'
       ] = upload_images_from_azure_blob_to_project


def upload_video_to_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "upload_video_to_project",
        "properties":
            {
                "project_name": get_project_name(project),
                "FPS": bool(args[2:3] or kwargs.get("target_fps", None)),
                "Start": bool(args[3:4] or kwargs.get("start_time", None)),
                "End": bool(args[4:5] or kwargs.get("end_time", None))
            }
    }


parsers['upload_video_to_project'] = upload_video_to_project


def attach_image_urls_to_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "attach_image_urls_to_project",
        "properties":
            {
                "project_name":
                    get_project_name(project),
                "Image Names":
                    bool(args[1:2] or kwargs.get("attachments", None)),
                "Annotation Status":
                    bool(args[2:3] or kwargs.get("annotation_status", None))
            }
    }


parsers['attach_image_urls_to_project'] = attach_image_urls_to_project


def set_images_annotation_statuses(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    annotation_status = kwargs.get("annotation_status", None)
    if not annotation_status:
        annotation_status = args[2:3][0]

    image_names = kwargs.get("image_names", [])
    if not image_names:
        image_names = args[1:2][0]

    return {
        "event_name": "set_images_annotation_statuses",
        "properties":
            {
                "project_name": get_project_name(project),
                "Image Count": len(image_names),
                "Annotation Status": annotation_status
            }
    }


parsers['set_images_annotation_statuses'] = set_images_annotation_statuses


def get_image_annotations(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "get_image_annotations",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['get_image_annotations'] = get_image_annotations


def get_image_preannotations(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "get_image_preannotations",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['get_image_preannotations'] = get_image_preannotations


def download_image_annotations(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "download_image_annotations",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['download_image_annotations'] = download_image_annotations


def download_image_preannotations(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "download_image_preannotations",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['download_image_preannotations'] = download_image_preannotations




def get_image_metadata(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "get_image_metadata",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['get_image_metadata'] = get_image_metadata




def get_image_bytes(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "get_image_bytes",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['get_image_bytes'] = get_image_bytes



def delete_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "delete_image",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['delete_image'] = delete_image



def add_annotation_comment_to_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "add_annotation_comment_to_image",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['add_annotation_comment_to_image'] = add_annotation_comment_to_image



def delete_annotation_class(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "delete_annotation_class",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['delete_annotation_class'] = delete_annotation_class




def get_annotation_class_metadata(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "get_annotation_class_metadata",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['get_annotation_class_metadata'] = get_annotation_class_metadata




def download_annotation_classes_json(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "download_annotation_classes_json",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['download_annotation_classes_json'] = download_annotation_classes_json



def search_annotation_classes(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "search_annotation_classes",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['search_annotation_classes'] = search_annotation_classes


def unshare_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "unshare_project",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['unshare_project'] = unshare_project



def get_project_image_count(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "get_project_image_count",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['get_project_image_count'] = get_project_image_count



def get_project_settings(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "get_project_settings",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['get_project_settings'] = get_project_settings




def set_project_settings(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "set_project_settings",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['set_project_settings'] = set_project_settings



def get_project_default_image_quality_in_editor(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "get_project_default_image_quality_in_editor",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['get_project_default_image_quality_in_editor'] = get_project_default_image_quality_in_editor


def get_project_metadata(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "get_project_metadata",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['get_project_metadata'] = get_project_metadata


def delete_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "delete_project",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['delete_project'] = delete_project




def rename_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "rename_project",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['rename_project'] = rename_project




def get_project_workflow(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "get_project_workflow",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['get_project_workflow'] = get_project_workflow



def set_project_workflow(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "set_project_workflow",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['set_project_workflow'] = set_project_workflow




def create_folder(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "create_folder",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['create_folder'] = create_folder




def get_folder_metadata(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "get_folder_metadata",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['get_folder_metadata'] = get_folder_metadata




def get_project_and_folder_metadata(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "get_project_and_folder_metadata",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['get_project_and_folder_metadata'] = get_project_and_folder_metadata





def rename_folder(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "rename_folder",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['rename_folder'] = rename_folder



def stop_model_training(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "stop_model_training",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['stop_model_training'] = stop_model_training



def download_model(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "download_model",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['download_model'] = download_model



def plot_model_metrics(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "plot_model_metrics",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['plot_model_metrics'] = plot_model_metrics


def delete_model(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "delete_model",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['delete_model'] = delete_model



def convert_project_type(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "convert_project_type",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['convert_project_type'] = convert_project_type



def convert_json_version(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "convert_json_version",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['convert_json_version'] = convert_json_version



def df_to_annotations(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "df_to_annotations",
        "properties": {
            "project_name": get_project_name(project),
        }
    }


parsers['df_to_annotations'] = df_to_annotations



def upload_image_annotations(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "upload_image_annotations",
        "properties": {
            "project_name": get_project_name(project),
            "Pixel" :  bool(args[3:4] or ("mask" in kwargs) ),
        }
    }

parsers['upload_image_annotations'] = upload_image_annotations







def download_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "download_image",
        "properties": {
            "project_name": get_project_name(project),
            "Download Annotations": bool(args[3:4] or ("include_annotations" in kwargs) ),
            "Download Fuse": bool(args[4:5] or ("include_fuse" in kwargs) ),
            "Download Overlay": bool(args[5:6] or ("include_overlay" in kwargs) ),
        }
    }

parsers['download_image'] = download_image






def copy_image(*args, **kwargs):
    project = kwargs.get("source_project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "copy_image",
        "properties": {
            "project_name": get_project_name(project),
            "Copy Annotations": bool(args[3:4] or ("include_annotations" in kwargs) ),
            "Copy Annotation Status": bool(args[4:5] or ("copy_annotation_status" in kwargs) ),
            "Copy Pin": bool(args[5:6] or ("copy_pin" in kwargs) ),
        }
    }

parsers['copy_image'] = copy_image




def move_image(*args, **kwargs):
    project = kwargs.get("source_project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "move_image",
        "properties": {
            "project_name": get_project_name(project),
            "Move Annotations": bool(args[3:4] or ("include_annotations" in kwargs) ),
            "Move Annotation Status": bool(args[4:5] or ("copy_annotation_status" in kwargs) ),
            "Move Pin": bool(args[5:6] or ("copy_pin" in kwargs) ),
        }
    }

parsers['move_image'] = move_image


def pin_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "pin_image",
        "properties": {
            "project_name": get_project_name(project),
            "Pin": bool(args[2:3] or ("pin" in kwargs) ),
        }
    }

parsers['pin_image'] = pin_image




def create_fuse_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    project_type = kwargs.get("project_type", None)
    if not project_type:
        project_type = args[2:3][0]

    return {
        "event_name": "create_fuse_image",
        "properties": {
            "project_name": get_project_name(project),
            "Project Type": project_type,
            "Overlay": bool(args[4:5] or ("output_overlay" in kwargs) ),
        }
    }

parsers['create_fuse_image'] = create_fuse_image





def set_image_annotation_status(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "set_image_annotation_status",
        "properties": {
            "project_name": get_project_name(project),
            "Annotation Status": bool(args[2:3] or ("annotation_status" in kwargs) ),
        }
    }

parsers['set_image_annotation_status'] = set_image_annotation_status




def add_annotation_bbox_to_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "add_annotation_bbox_to_image",
        "properties": {
            "project_name": get_project_name(project),
            "Attributes": bool(args[4:5] or ("annotation_class_attributes" in kwargs) ),
            "Error": bool(args[5:6] or ("error" in kwargs) ),

        }
    }

parsers['add_annotation_bbox_to_image'] = add_annotation_bbox_to_image



def add_annotation_polygon_to_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "add_annotation_polygon_to_image",
        "properties": {
            "project_name": get_project_name(project),
            "Attributes": bool(args[4:5] or ("annotation_class_attributes" in kwargs) ),
            "Error": bool(args[5:6] or ("error" in kwargs) ),

        }
    }

parsers['add_annotation_polygon_to_image'] = add_annotation_polygon_to_image



def add_annotation_polyline_to_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "add_annotation_polyline_to_image",
        "properties": {
            "project_name": get_project_name(project),
            "Attributes": bool(args[4:5] or ("annotation_class_attributes" in kwargs) ),
            "Error": bool(args[5:6] or ("error" in kwargs) ),

        }
    }

parsers['add_annotation_polyline_to_image'] = add_annotation_polyline_to_image



def add_annotation_point_to_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "add_annotation_point_to_image",
        "properties": {
            "project_name": get_project_name(project),
            "Attributes": bool(args[4:5] or ("annotation_class_attributes" in kwargs) ),
            "Error": bool(args[5:6] or ("error" in kwargs) ),

        }
    }

parsers['add_annotation_point_to_image'] = add_annotation_point_to_image


def add_annotation_ellipse_to_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "add_annotation_ellipse_to_image",
        "properties": {
            "project_name": get_project_name(project),
            "Attributes": bool(args[4:5] or ("annotation_class_attributes" in kwargs) ),
            "Error": bool(args[5:6] or ("error" in kwargs) ),

        }
    }

parsers['add_annotation_ellipse_to_image'] = add_annotation_ellipse_to_image




def add_annotation_template_to_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "add_annotation_template_to_image",
        "properties": {
            "project_name": get_project_name(project),
            "Attributes": bool(args[5:6] or ("annotation_class_attributes" in kwargs) ),
            "Error": bool(args[6:7] or ("error" in kwargs) ),

        }
    }

parsers['add_annotation_template_to_image'] = add_annotation_template_to_image





def add_annotation_cuboid_to_image(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "add_annotation_cuboid_to_image",
        "properties": {
            "project_name": get_project_name(project),
            "Attributes": bool(args[4:5] or ("annotation_class_attributes" in kwargs) ),
            "Error": bool(args[5:6] or ("error" in kwargs) ),

        }
    }

parsers['add_annotation_cuboid_to_image'] = add_annotation_cuboid_to_image




def create_annotation_class(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "create_annotation_class",
        "properties": {
            "project_name": get_project_name(project),
            "Attributes": bool(args[3:4] or ("attribute_groups" in kwargs) ),
        }
    }

parsers['create_annotation_class'] = create_annotation_class



def create_annotation_classes_from_classes_json(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    return {
        "event_name": "create_annotation_classes_from_classes_json",
        "properties": {
            "project_name": get_project_name(project),
            "From S3": bool(args[2:3] or ("from_s3_bucket" in kwargs) ),
        }
    }

parsers['create_annotation_classes_from_classes_json'] = create_annotation_classes_from_classes_json




def class_distribution(*args, **kwargs):
    return {
        "event_name": "class_distribution",
        "properties": {
            "Plot": bool(args[2:3] or ("visualize" in kwargs) ),
        }
    }

parsers['class_distribution'] = class_distribution



def attribute_distribution(*args, **kwargs):
    return {
        "event_name": "attribute_distribution",
        "properties": {
            "Plot": bool(args[2:3] or ("visualize" in kwargs) ),
        }
    }

parsers['attribute_distribution'] = attribute_distribution


def share_project(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    user_role = kwargs.get("user_role", None)
    if not user_role:
        user_role = args[2:3][0]

    
    return {
        "event_name": "share_project",
        "properties": {
            "project_name": get_project_name(project),
            "User Role":user_role
        }
    }

parsers['share_project'] = share_project



def set_project_default_image_quality_in_editor(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]

    image_quality_in_editor = kwargs.get("image_quality_in_editor", None)
    if not image_quality_in_editor:
        image_quality_in_editor = args[1:2][0]

    
    return {
        "event_name": "set_project_default_image_quality_in_editor",
        "properties": {
            "project_name": get_project_name(project),
            "Image Quality":image_quality_in_editor
        }
    }

parsers['set_project_default_image_quality_in_editor'] = set_project_default_image_quality_in_editor



def get_exports(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]
    
    return {
        "event_name": "get_exports",
        "properties": {
            "project_name": get_project_name(project),
            "Metadata": bool(args[1:2] or ("return_metadata" in kwargs) ),
        }
    }

parsers['get_exports'] = get_exports




def search_folders(*args, **kwargs):
    project = kwargs.get("project", None)
    if not project:
        project = args[0:1][0]
    
    return {
        "event_name": "search_folders",
        "properties": {
            "project_name": get_project_name(project),
            "Metadata": bool(args[2:3] or ("return_metadata" in kwargs) ),
        }
    }

parsers['search_folders'] = search_folders



def filter_images_by_tags(*args, **kwargs):
    return {
        "event_name": "filter_images_by_tags",
        "properties": {
            "Include": bool(args[1:2] or ("include" in kwargs) ),
            "Exclude" : bool(args[2:3] or ("exclude" in kwargs) )
        }
    }

parsers['filter_images_by_tags'] = filter_images_by_tags



def filter_images_by_comments(*args, **kwargs):
    return {
        "event_name": "filter_images_by_comments",
        "properties": {
            "Include Unresolved Comments" : bool(args[1:2] or ("include_unresolved_comments" in kwargs) ),
            "Include Resolved Comments": bool(args[2:3] or ("include_resolved_comments" in kwargs) )
        }
    }

parsers['filter_images_by_comments'] = filter_images_by_comments



def filter_annotation_instances(*args, **kwargs):
    return {
        "event_name": "filter_annotation_instances",
        "properties": {
            "Include" : bool(args[1:2] or ("include" in kwargs) ),
            "Exclude": bool(args[2:3] or ("exclude" in kwargs) )
        }
    }

parsers['filter_annotation_instances'] = filter_annotation_instances




def aggregate_annotations_as_df(*args, **kwargs):
    folder_names = kwargs.get("folder_names", None)
    if not folder_names:
        folder_names = args[5:6]
        if folder_names:
            folder_names = args[5:6][0]
        else:
            folder_names = []


    return {
        "event_name": "aggregate_annotations_as_df",
        "properties": {
            "Fodler Count" : len(folder_names),
        }
    }

parsers['aggregate_annotations_as_df'] = aggregate_annotations_as_df




