import numpy as np


def _create_sa_classes(classes):
    sa_classes_loader = []
    for key, value in classes.items():
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)
        sa_classes = {'name': key, 'color': hexcolor, 'attribute_groups': []}
        attribute_groups = []
        for attr_group_key, attr_group in value['attribute_group'].items():
            attr_loader = {
                'name': attr_group_key,
                'is_multiselect': attr_group['is_multiselect'],
                'attributes': []
            }
            for attr in set(attr_group['attributes']):
                attr_loader['attributes'].append({'name': attr})
            if attr_loader:
                attribute_groups.append(attr_loader)

        sa_classes['attribute_groups'] = attribute_groups

        sa_classes_loader.append(sa_classes)
    return sa_classes_loader


def _update_classes_dict(classes, new_class, new_attributes):
    if new_class not in classes.keys():
        classes[new_class] = {'attribute_group': {}}
        classes[new_class]['attribute_group']['converted_attributes'] = {}
        classes[new_class]['attribute_group']['converted_attributes'][
            'is_multiselect'] = 1
        classes[new_class]['attribute_group']['converted_attributes'][
            'attributes'] = new_attributes
    else:
        classes[new_class]['attribute_group']['converted_attributes'][
            'attributes'] += new_attributes
    return classes


def _create_attributes_list(dl_attributes):
    attributes = []
    for attribute in dl_attributes:
        attr = {'name': attribute, 'groupName': 'converted_attributes'}
        attributes.append(attr)
    return attributes
