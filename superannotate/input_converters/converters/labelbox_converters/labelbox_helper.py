import requests
import logging

logger = logging.getLogger("superannotate-python-sdk")


def image_downloader(url, file_name):
    logger.info("Downloading mask for {}".format(file_name))
    r = requests.get(url, stream=True)
    with open(file_name, 'wb') as f:
        f.write(r.content)


def _create_classes_json(classes):
    sa_classes_loader = []
    for key, value in classes.items():
        sa_classes = {
            'name': key,
            'color': value['color'],
            'attribute_groups': []
        }
        attribute_groups = []
        for attr_group_key, attr_group in value['attribute_groups'].items():
            attr_loader = {
                'name': attr_group_key,
                'is_multiselect': attr_group['is_multiselect'],
                'attributes': []
            }
            for attr in attr_group['attributes']:
                attr_loader['attributes'].append({'name': attr})
            if attr_loader:
                attribute_groups.append(attr_loader)
        sa_classes['attribute_groups'] = attribute_groups

        sa_classes_loader.append(sa_classes)

    return sa_classes_loader


def _create_classes_id_map(json_data):
    classes = {}
    for d in json_data:
        if 'objects' not in d['Label'].keys():
            continue

        instances = d["Label"]["objects"]
        for instance in instances:
            class_name = instance["value"]
            if class_name not in classes.keys():
                color = instance["color"]
                classes[class_name] = {"color": color, 'attribute_groups': {}}

            if 'classifications' in instance.keys():
                classifications = instance['classifications']
                for classification in classifications:
                    if classification['value'] not in classes[class_name][
                        'attribute_groups']:
                        if 'answer' in classification.keys():
                            if isinstance(classification['answer'], str):
                                continue

                            classes[class_name]['attribute_groups'][
                                classification['value']] = {
                                    'is_multiselect': 0,
                                    'attributes': []
                                }
                            classes[class_name]['attribute_groups'][
                                classification['value']]['attributes'].append(
                                    classification['answer']['value']
                                )

                        elif 'answers' in classification.keys():
                            classes[class_name]['attribute_groups'][
                                classification['value']] = {
                                    'is_multiselect': 1,
                                    'attributes': []
                                }
                            for attr in classification['answers']:
                                classes[class_name]['attribute_groups'][
                                    classification['value']
                                ]['attributes'].append(attr['value'])

                    else:
                        if 'answer' in classification.keys():
                            classes[class_name]['attribute_groups'][
                                classification['value']]['attributes'].append(
                                    classification['answer']['value']
                                )
                        elif 'answers' in classification.keys():
                            for attr in classification['answers']:
                                classes[class_name]['attribute_groups'][
                                    classification['value']
                                ]['attributes'].append(attr['value'])
    return classes


def _create_attributes_list(lb_attributes):
    attributes = []
    for attribute in lb_attributes:
        group_name = attribute['value']
        if 'answer' in attribute.keys(
        ) and isinstance(attribute['answer'], dict):
            attribute_name = attribute['answer']['value']
            attr_dict = {'name': attribute_name, 'groupName': group_name}
            attributes.append(attr_dict)
        elif 'answers' in attribute.keys():
            for attr in attribute['answers']:
                attribute_name = attr['value']
                attr_dict = {'name': attribute_name, 'groupName': group_name}
                attributes.append(attr_dict)

    return attributes
