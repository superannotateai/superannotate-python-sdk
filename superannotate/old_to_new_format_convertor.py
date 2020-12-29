import json
import os


def update_json_format(old_json_path, new_json_path, project_type):
    old_json_data = json.load(open(old_json_path))
    new_json_data = {
        "metadata": {},
        "instances": [],
        "tags": [],
        "comments": []
    }

    meta_keys = [
        "name", "width", "height", "status", "pinned", "isPredicted",
        "projectId", "annotatorEmail", "qaEmail"
    ]
    if project_type == "Pixel":
        meta_keys.append("isSegmented")

    new_json_data["metadata"] = dict.fromkeys(meta_keys)

    #set image name
    suffix = "___objects.json" if project_type == "Vector" else "___pixel.json"
    image_name = os.path.basename(old_json_path).split(suffix)[0]
    metadata = new_json_data["metadata"]
    metadata["name"] = image_name

    for item in old_json_data:
        object_type = item.get("type")
        #add metadata
        if object_type == "meta":
            meta_name = item["name"]
            if meta_name == "imageAttributes":
                metadata["height"] = item.get("height")
                metadata["width"] = item.get("width")
                metadata["status"] = item.get("status")
                metadata["pinned"] = item.get("pinned")
            if meta_name == "lastAction":
                metadata["lastAction"] = dict.fromkeys(["email", "timestamp"])
                metadata["lastAction"]["email"] = item.get("userId")
                metadata["lastAction"]["timestamp"] = item.get("timestamp")
        #add tags
        elif object_type == "tag":
            new_json_data["tags"].append(item.get("name"))
        #add comments
        elif object_type == "comment":
            item.pop("type")
            item["correspondence"] = item["comments"]
            for comment in item["correspondence"]:
                comment["email"] = comment["id"]
                comment.pop("id")
            item.pop("comments")
            new_json_data["comments"].append(item)
        #add instances
        else:
            new_json_data["instances"].append(item)

    with open(new_json_path, "w") as jf:
        json.dump(new_json_data, jf, indent=2)
