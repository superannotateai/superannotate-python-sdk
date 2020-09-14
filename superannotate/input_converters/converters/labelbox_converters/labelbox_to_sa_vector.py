import json
import os


def labelbox_object_detection_to_sa_vector(json_data, output_dir, id_generator):
    classes = {}
    sa_classes_loader = []
    for d in json_data:
        instances = d["Label"]["objects"]
        sa_loader = []
        for instance in instances:
            class_name = instance["title"]
            if class_name in classes.keys():
                index = classes[class_name]["index"]
                color = classes[class_name]["color"]
            else:
                index = next(id_generator)
                color = instance["color"]
                classes[class_name] = {"index": index, "color": color}

            if 'bbox' in instance.keys():
                x1 = instance['bbox']['left']
                x2 = instance['bbox']['left'] + instance['bbox']['width']
                y1 = instance['bbox']['top']
                y2 = instance['bbox']['top'] + instance['bbox']['height']
                points = {'x1': x1, 'x2': x2, 'y1': y1, 'y2': y2}
                ptype = 'bbox'
            elif 'polygon' in instance.keys():
                ptype = 'polygon'
                points = []
                for point in instance['polygon']:
                    points.append(point['x'])
                    points.append(point['y'])
            else:
                points = []
                ptype = ''

            sa_obj = {
                'type': ptype,
                'points': points,
                'className': class_name,
                'classId': classes[class_name]['index'],
                'attributes': [],
                'probability': 100,
                'locked': False,
                'visible': True,
                'groupId': 0,
            }
            sa_loader.append(sa_obj)

        file_name = d['External ID'] + '___objects.json'
        with open(os.path.join(output_dir, file_name), "w") as fw:
            json.dump(sa_loader, fw, indent=2)

    for key, value in classes.items():
        sa_classes = {
            'id': value['index'],
            'name': key,
            'color': value['color'],
            'attribute_groups': []
        }
        sa_classes_loader.append(sa_classes)

    with open(os.path.join(output_dir, 'classes', 'classes.json'), 'w') as fw:
        json.dump(sa_classes_loader, fw, indent=2)
