from pathlib import Path


def image_path_to_annotation_paths(image_path, project_type):
    image_path = Path(image_path)
    postfix_json = '___objects.json' if project_type == 1 else '___pixel.json'
    postfix_mask = '___save.png'
    if project_type == 1:
        return (image_path.parent / (image_path.name + postfix_json), )
    else:
        return (
            image_path.parent / (image_path.name + postfix_json),
            image_path.parent / (image_path.name + postfix_mask)
        )
