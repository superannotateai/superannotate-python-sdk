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


def labelbox_object_detection_to_sa_vector(json_data):
    classes = _create_classes_id_map(json_data)
    sa_jsons = {}
    for d in json_data:
        if 'objects' not in d['Label'].keys():
            file_name = d['External ID'] + '___objects.json'
            sa_jsons[file_name] = []
            continue

        instances = d["Label"]["objects"]
        sa_loader = []
        for instance in instances:
            class_name = instance["value"]
            attributes = []
            if 'classifications' in instance.keys():
                classifications = instance['classifications']
                for classification in classifications:
                    group_name = classification['value']
                    if 'answer' in classification.keys(
                    ) and isinstance(classification['answer'], dict):
                        attribute_name = classification['answer']['value']
                        attr_dict = {
                            'name': attribute_name,
                            'groupName': group_name
                        }
                        attributes.append(attr_dict)
                    elif 'answers' in classification.keys():
                        for attr in classification['answers']:
                            attribute_name = attr['value']
                            attr_dict = {
                                'name': attribute_name,
                                'groupName': group_name
                            }
                            attributes.append(attr_dict)
            sa_obj = {
                'className': class_name,
                'attributes': attributes,
                'probability': 100,
                'locked': False,
                'visible': True,
                'groupId': 0,
            }

            if 'bbox' in instance.keys():
                x1 = instance['bbox']['left']
                x2 = instance['bbox']['left'] + instance['bbox']['width']
                y1 = instance['bbox']['top']
                y2 = instance['bbox']['top'] + instance['bbox']['height']
                sa_obj['points'] = {'x1': x1, 'x2': x2, 'y1': y1, 'y2': y2}
                sa_obj['type'] = 'bbox'
                sa_loader.append(sa_obj)

        file_name = d['External ID'] + '___objects.json'
        sa_jsons[file_name] = sa_loader

    sa_classes = _create_classes_json(classes)
    return sa_jsons, sa_classes, None


def labelbox_instance_segmentation_to_sa_vector(json_data):
    classes = _create_classes_id_map(json_data)
    sa_jsons = {}
    for d in json_data:
        if 'objects' not in d['Label'].keys():
            file_name = d['External ID'] + '___objects.json'
            sa_jsons[file_name] = []
            continue

        instances = d["Label"]["objects"]
        sa_loader = []
        for instance in instances:
            class_name = instance["value"]
            attributes = []
            if 'classifications' in instance.keys():
                classifications = instance['classifications']
                for classification in classifications:
                    group_name = classification['value']
                    if 'answer' in classification.keys(
                    ) and isinstance(classification['answer'], dict):
                        attribute_name = classification['answer']['value']
                        attr_dict = {
                            'name': attribute_name,
                            'groupName': group_name
                        }
                        attributes.append(attr_dict)
                    elif 'answers' in classification.keys():
                        for attr in classification['answers']:
                            attribute_name = attr['value']
                            attr_dict = {
                                'name': attribute_name,
                                'groupName': group_name
                            }
                            attributes.append(attr_dict)

            sa_obj = {
                'className': class_name,
                'attributes': attributes,
                'probability': 100,
                'locked': False,
                'visible': True,
                'groupId': 0,
            }

            if 'polygon' in instance.keys():
                sa_obj['type'] = 'polygon'
                points = []
                for point in instance['polygon']:
                    points.append(point['x'])
                    points.append(point['y'])
                sa_obj['points'] = points
                sa_loader.append(sa_obj)

        file_name = d['External ID'] + '___objects.json'
        sa_jsons[file_name] = sa_loader

    sa_classes = _create_classes_json(classes)
    return sa_jsons, sa_classes, None


def labelbox_to_sa(json_data):
    classes = _create_classes_id_map(json_data)
    sa_jsons = {}
    for d in json_data:
        if 'objects' not in d['Label'].keys():
            file_name = d['External ID'] + '___objects.json'
            sa_jsons[file_name] = []
            continue

        instances = d["Label"]["objects"]
        sa_loader = []
        for instance in instances:
            class_name = instance["value"]
            attributes = []
            if 'classifications' in instance.keys():
                classifications = instance['classifications']
                for classification in classifications:
                    group_name = classification['value']
                    if 'answer' in classification.keys(
                    ) and isinstance(classification['answer'], dict):
                        attribute_name = classification['answer']['value']
                        attr_dict = {
                            'name': attribute_name,
                            'groupName': group_name
                        }
                        attributes.append(attr_dict)
                    elif 'answers' in classification.keys():
                        for attr in classification['answers']:
                            attribute_name = attr['value']
                            attr_dict = {
                                'name': attribute_name,
                                'groupName': group_name
                            }
                            attributes.append(attr_dict)

            sa_obj = {
                'className': class_name,
                'attributes': attributes,
                'probability': 100,
                'locked': False,
                'visible': True,
                'groupId': 0,
            }
            if 'polygon' in instance.keys():
                sa_obj['type'] = 'polygon'
                points = []
                for point in instance['polygon']:
                    points.append(point['x'])
                    points.append(point['y'])
                sa_obj['points'] = points
                sa_loader.append(sa_obj)
            elif 'bbox' in instance.keys():
                x1 = instance['bbox']['left']
                x2 = instance['bbox']['left'] + instance['bbox']['width']
                y1 = instance['bbox']['top']
                y2 = instance['bbox']['top'] + instance['bbox']['height']
                sa_obj['points'] = {'x1': x1, 'x2': x2, 'y1': y1, 'y2': y2}
                sa_obj['type'] = 'bbox'
                sa_loader.append(sa_obj)
            elif 'line' in instance.keys():
                sa_obj['type'] = 'polyline'
                points = []
                for point in instance['line']:
                    points.append(point['x'])
                    points.append(point['y'])
                sa_obj['points'] = points
                sa_loader.append(sa_obj)
            elif 'point' in instance.keys():
                sa_obj['points'] = {
                    'x': instance['point']['x'],
                    'y': instance['point']['y']
                }
                sa_obj['type'] = 'point'
                sa_loader.append(sa_obj)

        file_name = d['External ID'] + '___objects.json'
        sa_jsons[file_name] = sa_loader

    sa_classes = _create_classes_json(classes)
    return sa_jsons, sa_classes, None