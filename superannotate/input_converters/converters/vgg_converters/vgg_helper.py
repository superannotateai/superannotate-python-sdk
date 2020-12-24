import numpy as np


def _create_classes(class_id_map):
    sa_classes = []
    for key in class_id_map.keys():
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)
        dd = {'name': key, 'color': hexcolor, 'attribute_groups': []}
        for attributes, value in class_id_map[key]['attribute_groups'].items():
            attr_group = {
                'name': attributes,
                'is_multiselect': value['is_multiselect'],
                'attributes': []
            }
            for attribute in value['attributes']:
                attr = {'name': attribute, 'groupName': attributes}
                attr_group['attributes'].append(attr.copy())
            dd['attribute_groups'].append(attr_group.copy())
        sa_classes.append(dd)
    return sa_classes


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
