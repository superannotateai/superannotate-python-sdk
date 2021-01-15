import logging
import requests

logger = logging.getLogger("superannotate-python-sdk")


def image_downloader(url, file_name):
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open(file_name, 'wb') as f:
            f.write(r.content)
        return True
    return False


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
