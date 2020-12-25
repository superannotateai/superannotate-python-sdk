import numpy as np


def _create_attribute_list(attribute_dict, class_name, class_id_map):
    attr_keys = attribute_dict.keys()
    attributes = []
    for attr in attr_keys:
        if attr in class_id_map[class_name]['attribute_groups'].keys():
            group_name = attr
            if isinstance(attribute_dict[attr], dict):
                keys = attribute_dict[attr].keys()
            else:
                keys = [attribute_dict[attr]]

            for key in keys:
                if key not in class_id_map[class_name]['attribute_groups'][
                    attr]['attributes']:
                    class_id_map[class_name]['attribute_groups'][attr][
                        'attributes'].append(key)
                dd = {'name': key, 'groupName': group_name}
                attributes.append(dd.copy())

        else:
            multi = 0
            if isinstance(attribute_dict[attr], dict):
                multi = 1

            class_id_map[class_name]['attribute_groups'][attr] = {
                'is_multiselect': multi,
                'attributes': []
            }
    return attributes
