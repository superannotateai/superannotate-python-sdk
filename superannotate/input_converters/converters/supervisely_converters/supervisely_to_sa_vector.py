import os
import json


# Converts bitmaps to polygon
def _base64_to_polygon(bitmap):
    z = zlib.decompress(base64.b64decode(bitmap))
    n = np.frombuffer(z, np.uint8)
    mask = cv2.imdecode(n, cv2.IMREAD_UNCHANGED)[:, :, 3].astype(bool)
    contours, hierarchy = cv2.findContours(
        mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    segmentation = []

    for contour in contours:
        contour = contour.flatten().tolist()
        if len(contour) > 4:
            segmentation.append(contour)
        if len(segmentation) == 0:
            continue
    return segmentation


def supervisely_to_sa(json_files, class_id_map):
    sa_jsons = {}
    for json_file in json_files:
        file_name = os.path.splitext(os.path.basename(json_file)
                                    )[0] + '___objects.json'

        json_data = json.load(open(json_file))
        sa_loader = []

        for obj in json_data['objects']:
            if 'classTitle' in obj and obj['classTitle'] in class_id_map.keys():
                attributes = []
                if 'tags' in obj.keys():
                    for tag in obj['tags']:
                        group_id = class_id_map[obj['classTitle']
                                               ]['attr_group']['id']
                        group_name = class_id_map[obj['classTitle']
                                                 ]['attr_group']['group_name']
                        attr_id = class_id_map[obj['classTitle']]['attr_group'][
                            'attributes'][tag['name']]
                        attr_name = tag['name']
                        attributes.append(
                            {
                                'id': attr_id,
                                'name': attr_name,
                                'groupId': group_id,
                                'groupName': group_name
                            }
                        )

                    sa_obj = {
                        'type': '',
                        'points': [],
                        'className': obj['classTitle'],
                        'classId': class_id_map[obj['classTitle']]['id'],
                        'pointLabels': {},
                        'attributes': attributes,
                        'probability': 100,
                        'locked': False,
                        'visible': True,
                        'groupId': 0
                    }

                    if obj['geometryType'] == 'point':
                        del sa_obj['points']
                        sa_obj['type'] = 'point'
                        sa_obj['x'] = obj['points']['exterior'][0][0]
                        sa_obj['y'] = obj['points']['exterior'][0][1]

                    elif obj['geometryType'] == 'line':
                        sa_obj['type'] = 'polyline'
                        sa_obj['points'] = [
                            item for el in obj['points']['exterior']
                            for item in el
                        ]

                    elif obj['geometryType'] == 'rectangle':
                        sa_obj['type'] = 'bbox'
                        sa_obj['points'] = {
                            'x1': obj['points']['exterior'][0][0],
                            'y1': obj['points']['exterior'][0][1],
                            'x2': obj['points']['exterior'][1][0],
                            'y2': obj['points']['exterior'][1][1]
                        }

                    elif obj['geometryType'] == 'polygon':
                        sa_obj['type'] = 'polygon'
                        sa_obj['points'] = [
                            item for el in obj['points']['exterior']
                            for item in el
                        ]

                    # elif obj['geometryType'] == 'graph':
                    #     for temp in sa_template_loader:
                    #         if temp['className'] == name:
                    #             sa_obj = temp

                    elif obj['geometryType'] == 'bitmap':
                        for ppoints in _base64_to_polygon(
                            obj['bitmap']['data']
                        ):
                            sa_ppoints = [
                                x + obj['bitmap']['origin'][0] if i %
                                2 == 0 else x + obj['bitmap']['origin'][1]
                                for i, x in enumerate(ppoints)
                            ]
                            sa_obj['type'] = 'polygon'
                            sa_obj['points'] = sa_ppoints

                    sa_loader.append(sa_obj)

        sa_jsons[file_name] = sa_loader

    return sa_jsons