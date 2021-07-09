def _update_classes_dict(classes, new_class, new_attributes):
    if new_class not in classes.keys():
        classes[new_class] = {"attribute_group": {}}
        classes[new_class]["attribute_group"]["converted_attributes"] = {}
        classes[new_class]["attribute_group"]["converted_attributes"][
            "is_multiselect"
        ] = 1
        classes[new_class]["attribute_group"]["converted_attributes"][
            "attributes"
        ] = new_attributes
    else:
        classes[new_class]["attribute_group"]["converted_attributes"][
            "attributes"
        ] += new_attributes
    return classes


def _create_attributes_list(dl_attributes):
    attributes = []
    for attribute in dl_attributes:
        attr = {"name": attribute, "groupName": "converted_attributes"}
        attributes.append(attr)
    return attributes
