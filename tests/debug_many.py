import json
import os
import pathlib
import random
import shutil
import threading
from datetime import datetime

import superannotate as sa
from PIL import Image, ImageDraw, ImageFont

random.seed(datetime.now())


def return_json():
    """returns dict"""
    data_json = {
        'metadata':
            {
                'lastAction':
                    {
                        'email': 'davita@superannotate.com',
                        'timestamp': 1615381797112
                    },
                'width': 1600,
                'height': 1600,
                'name': '*.jpg'
            },
        'comments': [],
        'tags': [],
        'instances':
            [
                {
                    'type': 'cuboid',
                    'classId': 466471,
                    'className': 'CUBOID',
                    'probability': 100,
                    'points':
                        {
                            'f1':
                                {
                                    'x': random.uniform(300, 1400),
                                    'y': random.uniform(300, 1400)
                                },
                            'f2':
                                {
                                    'x': random.uniform(300, 1400),
                                    'y': random.uniform(300, 1400)
                                },
                            'r1':
                                {
                                    'x': random.uniform(300, 1400),
                                    'y': random.uniform(300, 1400)
                                },
                            'r2':
                                {
                                    'x': random.uniform(300, 1400),
                                    'y': random.uniform(300, 1400)
                                }
                        },
                    'groupId': 0,
                    'pointLabels': {},
                    'locked': False,
                    'visible': True,
                    'attributes': [],
                    'trackingId': None,
                    'error': None,
                    'createdAt': '2021-03-10T15: 05: 39.200Z',
                    'createdBy':
                        {
                            'email': 'davita@superannotate.com',
                            'role': 'Admin'
                        },
                    'creationType': 'Manual',
                    'updatedAt': '2021-03-10T15: 05: 47.495Z',
                    'updatedBy':
                        {
                            'email': 'davita@superannotate.com',
                            'role': 'Admin'
                        }
                }, {
                    'type': 'ellipse',
                    'classId': 466473,
                    'className': 'ELLIPSE',
                    'probability': 100,
                    'cx': random.uniform(300, 1400),
                    'cy': random.uniform(300, 1400),
                    'rx': random.uniform(300, 1400),
                    'ry': random.uniform(300, 1400),
                    'angle': 0,
                    'groupId': 0,
                    'pointLabels': {},
                    'locked': False,
                    'visible': True,
                    'attributes': [],
                    'trackingId': None,
                    'error': None,
                    'createdAt': '2021-03-10T15: 05: 26.962Z',
                    'createdBy':
                        {
                            'email': 'davita@superannotate.com',
                            'role': 'Admin'
                        },
                    'creationType': 'Manual',
                    'updatedAt': '2021-03-10T15: 05: 30.690Z',
                    'updatedBy':
                        {
                            'email': 'davita@superannotate.com',
                            'role': 'Admin'
                        }
                }, {
                    'type': 'bbox',
                    'classId': 466172,
                    'className': 'BBOX',
                    'probability': 100,
                    'points':
                        {
                            'x1': random.uniform(300, 1400),
                            'x2': random.uniform(300, 1400),
                            'y1': random.uniform(300, 1400),
                            'y2': random.uniform(300, 1400)
                        },
                    'groupId': 0,
                    'pointLabels': {},
                    'locked': False,
                    'visible': True,
                    'attributes': [],
                    'trackingId': None,
                    'error': None,
                    'createdAt': '2021-03-10T15: 05: 11.085Z',
                    'createdBy':
                        {
                            'email': 'davita@superannotate.com',
                            'role': 'Admin'
                        },
                    'creationType': 'Manual',
                    'updatedAt': '2021-03-10T15: 05: 23.677Z',
                    'updatedBy':
                        {
                            'email': 'davita@superannotate.com',
                            'role': 'Admin'
                        }
                }, {
                    'type': 'polygon',
                    'classId': 466173,
                    'className': 'POLYGON',
                    'probability': 100,
                    'points':
                        [
                            random.uniform(300, 1400),
                            random.uniform(300, 1400),
                            random.uniform(300, 1400),
                            random.uniform(300, 1400),
                            random.uniform(300, 1400),
                            random.uniform(300, 1400)
                        ],
                    'groupId': 0,
                    'pointLabels': {},
                    'locked': False,
                    'visible': True,
                    'attributes': [],
                    'trackingId': None,
                    'error': None,
                    'createdAt': '2021-03-10T15: 04: 57.385Z',
                    'createdBy':
                        {
                            'email': 'davita@superannotate.com',
                            'role': 'Admin'
                        },
                    'creationType': 'Manual',
                    'updatedAt': '2021-03-10T15: 05: 06.794Z',
                    'updatedBy':
                        {
                            'email': 'davita@superannotate.com',
                            'role': 'Admin'
                        }
                }, {
                    'type': 'polyline',
                    'classId': 466175,
                    'className': 'POLYLINE',
                    'probability': 100,
                    'points':
                        [
                            random.uniform(300, 1400),
                            random.uniform(300, 1400),
                            random.uniform(300, 1400),
                            random.uniform(300, 1400),
                            random.uniform(300, 1400),
                            random.uniform(300, 1400),
                            random.uniform(300, 1400),
                            random.uniform(300, 1400),
                            random.uniform(300, 1400),
                            random.uniform(300, 1400),
                            random.uniform(300, 1400),
                            random.uniform(300, 1400)
                        ],
                    'groupId': 0,
                    'pointLabels': {},
                    'locked': False,
                    'visible': True,
                    'attributes': [],
                    'trackingId': None,
                    'error': None,
                    'createdAt': '2021-03-10T15: 04: 37.760Z',
                    'createdBy':
                        {
                            'email': 'davita@superannotate.com',
                            'role': 'Admin'
                        },
                    'creationType': 'Manual',
                    'updatedAt': '2021-03-10T15: 04: 50.880Z',
                    'updatedBy':
                        {
                            'email': 'davita@superannotate.com',
                            'role': 'Admin'
                        }
                }
            ]
    }
    return data_json


def draw_rectangle(draw, width, height, fnt):
    """Gets draw object fills with rectangles"""
    for s_h in range(0, height - 100, 200):
        for s_w in range(0, width - 100, 200):
            draw.rectangle(
                ((s_w + 50, s_h), (s_w + 150, s_h + 100)), fill="yellow"
            )


def create_json(img_name):
    """Creates json for particular image"""
    data_json = return_json()
    data_json['metadata']['name'] = img_name
    with open('annotations/%s___objects.json' % img_name, 'w') as out:
        json.dump(data_json, out)


def create_img(width, height, ind, fnt):
    """Creates Image"""
    img = Image.new(
        'RGB', (height, width),
        color=(
            random.randint(0, 255), random.randint(0,
                                                   255), random.randint(0, 255)
        )
    )
    draw = ImageDraw.Draw(img)
    draw_rectangle(draw, width, height, fnt)
    text_w, text_h = draw.textsize(str(ind))
    draw.text(
        ((height - text_h) / 4, (width - text_w) / 2),
        "%s" % ind,
        font=fnt,
        fill=(0, 0, 0)
    )
    img_name = '%s.jpg' % ind
    img.save('images/%s' % img_name)
    create_json(img_name)


def generate_images(width, height, count):
    """Main function"""
    fnt = ImageFont.load_default()
    thread_list = []
    for ind in range(count):
        thread = threading.Thread(
            target=create_img, args=(height, width, ind, fnt)
        )
        thread_list.append(thread)
    for thread in thread_list:
        thread.start()
    for thread in thread_list:
        thread.join()
    #for ind in range(1000000, count):
    #    create_img(height, width, ind, fnt)


def sdk_uplaod(project_name, image_path):
    """Upload Images via SA sdk"""
    project_metadata = sa.get_project_metadata(project_name)
    _uploaded, _skipped, _duplicate = sa.upload_images_from_folder_to_project(
        project=project_metadata["name"], folder_path="./images"
    )
    sa.upload_annotations_from_folder_to_project(project_name, "./annotations")


if __name__ == "__main__":
    height = 1600
    width = 1600
    count = 100
    project_name = "Large Dataset2"
    image_path = "./images"
    sa.create_project(project_name, "x", "Vector")
    sa.create_annotation_class(project_name, "CUBOID", "#FFFFFF")
    sa.create_annotation_class(project_name, "BBOX", "#FFFFFF")
    sa.create_annotation_class(project_name, "POLYGON", "#FFFFFF")
    sa.create_annotation_class(project_name, "POLYLINE", "#FFFFFF")
    sa.create_annotation_class(project_name, "ELLIPSE", "#FFFFFF")
    if os.path.exists("./images"):
        shutil.rmtree("./images")
    if os.path.exists("./annotations"):
        shutil.rmtree("./annotations")
    pathlib.Path("./images").mkdir(exist_ok=True)
    pathlib.Path("./annotations").mkdir(exist_ok=True)
    generate_images(width, height, count)
    sdk_uplaod(project_name, image_path)
