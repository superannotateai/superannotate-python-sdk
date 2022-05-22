from unittest import TestCase

from src.superannotate.lib.core.video_convertor import VideoFrameGenerator

TEST_SMALL_ANNOTATION = {
    "metadata": {"name": "blue cat", "width": 848, "height": 476, "status": "InProgress",
                 "url": "https://drive.google.com/uc?export=download&id=1BNs7sQqWv0tnQtZYiDhHXUzKTS0mUk3X",
                 "duration": 2817000, "projectId": 226935, "error": None, "annotatorEmail": None,
                 "qaEmail": None,
                 "lastAction": {"timestamp": 1652277982880, "email": "arturn@superannotate.com"}},
    "instances": [{"meta": {"type": "bbox", "classId": 1740965, "className": "class",
                            "pointLabels": {},
                            "createdBy": {"email": "arturn@superannotate.com", "role": "Admin"},
                            "createdAt": "2022-05-11T14:06:20.992Z",
                            "updatedBy": {"email": "arturn@superannotate.com", "role": "Admin"},
                            "updatedAt": "2022-05-11T14:06:22.874Z", "start": 203033,
                            "end": 744547}, "parameters": [{"start": 203033, "end": 744547,
                                                            "timestamps": [{"points": {
                                                                "x1": 45.73,
                                                                "y1": 226.8,
                                                                "x2": 208.93,
                                                                "y2": 373.74
                                                            },
                                                                "timestamp": 203033,
                                                                "attributes": []}, {
                                                                "points": {
                                                                    "x1": 45.73,
                                                                    "y1": 226.8,
                                                                    "x2": 208.93,
                                                                    "y2": 373.74},
                                                                "timestamp": 744547,
                                                                "attributes": []}]}]}],
    "tags": ["gff"]}

TEST_ANNOTATION = {"metadata": {"name": "video_file_example_1", "width": 1920, "height": 1080, "status": "InProgress",
                                "url": "https://sa-public-files.s3.us-west-2.amazonaws.com/Video+project/video_file_example_1.mp4",
                                "duration": 30526667, "projectId": 202655, "error": None, "annotatorEmail": None,
                                "qaEmail": None,
                                "lastAction": {"timestamp": 1652789740739, "email": "arturn@superannotate.com"}},
                   "instances":
                       [
                           {"meta": {"type": "bbox", "classId": 1379945, "className": "tree", "pointLabels": {},
                                     "createdBy": {"email": "arturn@superannotate.com", "role": "Admin"},
                                     "createdAt": "2022-03-02T12:23:10.887Z",
                                     "updatedBy": {"email": "arturn@superannotate.com", "role": "Admin"},
                                     "updatedAt": "2022-05-17T12:15:40.728Z", "start": 0, "end": 2515879},
                            "parameters": [{"start": 0, "end": 2515879, "timestamps": [
                                {"points": {"x1": 496.13, "y1": 132.02, "x2": 898.05, "y2": 515.25},
                                 "timestamp": 0, "attributes": [
                                    {"id": 2699916, "groupId": 1096002, "name": "standing",
                                     "groupName": "state"}]},
                                {"points": {"x1": 744.37, "y1": 66.41, "x2": 1146.29, "y2": 449.64},
                                 "timestamp": 640917, "attributes": [
                                    {"id": 2699917, "groupId": 1096002, "name": "falling",
                                     "groupName": "state"}]},
                                {"points": {"x1": 857.56, "y1": 227.21, "x2": 1259.48, "y2": 610.44},
                                 "timestamp": 1215864, "attributes": [
                                    {"id": 2699917, "groupId": 1096002, "name": "falling",
                                     "groupName": "state"}]},
                                {"points": {"x1": 857.56, "y1": 227.21, "x2": 1259.48, "y2": 610.44},
                                 "timestamp": 1572238, "attributes": [
                                    {"id": 2699916, "groupId": 1096002, "name": "standing",
                                     "groupName": "state"}]},
                                {"points": {"x1": 1038.3, "y1": 270.54, "x2": 1440.22, "y2": 653.77},
                                 "timestamp": 2255379, "attributes": [
                                    {"id": 2699916, "groupId": 1096002, "name": "standing",
                                     "groupName": "state"}]},
                                {"points": {"x1": 1038.3, "y1": 270.54, "x2": 1440.22, "y2": 653.77},
                                 "timestamp": 2515879, "attributes": [
                                    {"id": 2699917, "groupId": 1096002, "name": "falling",
                                     "groupName": "state"}]}]}]}, {
                           "meta": {"type": "bbox", "classId": 1379945, "className": "tree",
                                    "pointLabels": {},
                                    "createdBy": {"email": "arturn@superannotate.com", "role": "Admin"},
                                    "createdAt": "2022-03-02T12:36:52.126Z",
                                    "updatedBy": {"email": "arturn@superannotate.com", "role": "Admin"},
                                    "updatedAt": "2022-03-02T12:38:24.056Z", "start": 2790828,
                                    "end": 5068924}, "parameters": [{"start": 2790828, "end": 5068924,
                                                                     "timestamps": [{"points": {"x1": 507.3,
                                                                                                "y1": 569.55,
                                                                                                "x2": 979.58,
                                                                                                "y2": 965.84},
                                                                                     "timestamp": 2790828,
                                                                                     "attributes": []}, {
                                                                                        "points": {
                                                                                            "x1": 507.3,
                                                                                            "y1": 569.55,
                                                                                            "x2": 979.58,
                                                                                            "y2": 965.84},
                                                                                        "timestamp": 2888183,
                                                                                        "attributes": [
                                                                                            {"id": 2699917,
                                                                                             "groupId": 1096002,
                                                                                             "name": "falling",
                                                                                             "groupName": "state"}]},
                                                                                    {"points": {"x1": 507.3,
                                                                                                "y1": 569.55,
                                                                                                "x2": 979.58,
                                                                                                "y2": 965.84},
                                                                                     "timestamp": 5068924,
                                                                                     "attributes": [
                                                                                         {"id": 2699917,
                                                                                          "groupId": 1096002,
                                                                                          "name": "falling",
                                                                                          "groupName": "state"}]}]}]
                       },
                           {
                               "meta": {"type": "bbox", "classId": 1379946, "className": "car", "pointLabels": {},
                                        "createdBy": {"email": "arturn@superannotate.com", "role": "Admin"},
                                        "createdAt": "2022-03-02T12:39:19.970Z",
                                        "updatedBy": {"email": "arturn@superannotate.com", "role": "Admin"},
                                        "updatedAt": "2022-03-02T12:41:13.536Z", "start": 4502645, "end": 6723950},
                               "parameters": [{"start": 4502645, "end": 6723950, "timestamps": [
                                   {"points": {"x1": 792.08, "y1": 671.23, "x2": 1178.97, "y2": 987.47},
                                    "timestamp": 4502645, "attributes": []},
                                   {"points": {"x1": 792.08, "y1": 671.23, "x2": 1178.97, "y2": 987.47},
                                    "timestamp": 5330158, "attributes": [
                                       {"id": 2699918, "groupId": 1096003, "name": "goes", "groupName": "movement"},
                                       {"id": 2699920, "groupId": 1096004, "name": "lights_on",
                                        "groupName": "lights"}]},
                                   {"points": {"x1": 792.08, "y1": 671.23, "x2": 1178.97, "y2": 987.47},
                                    "timestamp": 5825043, "attributes": [
                                       {"id": 2699920, "groupId": 1096004, "name": "lights_on",
                                        "groupName": "lights"}, {"id": 2699919, "groupId": 1096003, "name": "stops",
                                                                 "groupName": "movement"}]},
                                   {"points": {"x1": 792.08, "y1": 671.23, "x2": 1178.97, "y2": 987.47},
                                    "timestamp": 6303703, "attributes": [
                                       {"id": 2699919, "groupId": 1096003, "name": "stops", "groupName": "movement"},
                                       {"id": 2699921, "groupId": 1096004, "name": "lights_off",
                                        "groupName": "lights"}]},
                                   {"points": {"x1": 792.08, "y1": 671.23, "x2": 1178.97, "y2": 987.47},
                                    "timestamp": 6723950, "attributes": [
                                       {"id": 2699919, "groupId": 1096003, "name": "stops", "groupName": "movement"},
                                       {"id": 2699921, "groupId": 1096004, "name": "lights_off",
                                        "groupName": "lights"}]}]}]
                           },
                           {
                               "meta": {"type": "event", "classId": 1379946, "className": "car",
                                        "createdBy": {"email": "arturn@superannotate.com", "role": "Admin"},
                                        "createdAt": "2022-03-02T12:41:39.135Z",
                                        "updatedBy": {"email": "arturn@superannotate.com", "role": "Admin"},
                                        "updatedAt": "2022-03-02T12:41:39.135Z", "start": 1655026,
                                        "end": 3365220}, "parameters": [{"start": 1655026, "end": 3365220,
                                                                         "timestamps": [{"timestamp": 1655026,
                                                                                         "attributes": []},
                                                                                        {"timestamp": 3365220,
                                                                                         "attributes": []}]}]
                           },
                           {
                               "meta": {
                                   "type": "point", "classId": 1379946, "className": "car",
                                   "createdBy": {"email": "arturn@superannotate.com", "role": "Admin"},
                                   "createdAt": "2022-05-17T11:38:50.041Z",
                                   "updatedBy": {"email": "arturn@superannotate.com", "role": "Admin"},
                                   "updatedAt": "2022-05-17T11:50:57.784Z", "start": 617519, "end": 2342388},
                               "parameters": [
                                   {
                                       "start": 617519, "end": 2342388, "timestamps": [
                                       {
                                           "x": 612.81, "y": 606.79, "timestamp": 617519, "attributes": [
                                           {
                                               "id": 2699918, "groupId": 1096003, "name": "goes",
                                               "groupName": "movement"},
                                           {"id": 2699920, "groupId": 1096004, "name": "lights_on",
                                            "groupName": "lights"}]},
                                       {"x": 653.05, "y": 648.81, "timestamp": 1266439,
                                        "attributes": [
                                            {"id": 2699918, "groupId": 1096003,
                                             "name": "goes", "groupName": "movement"},
                                            {"id": 2699920, "groupId": 1096004,
                                             "name": "lights_on",
                                             "groupName": "lights"}]},
                                       {"x": 691.9399999999999, "y": 682.7099999999999, "timestamp": 1569965,
                                        "attributes": [{"id": 2699918, "groupId": 1096003, "name": "goes",
                                                        "groupName": "movement"},
                                                       {"id": 2699921, "groupId": 1096004, "name": "lights_off",
                                                        "groupName": "lights"}]},
                                       {"x": 691.9399999999999, "y": 682.7099999999999, "timestamp": 2342388,
                                        "attributes": [{"id": 2699921, "groupId": 1096004, "name": "lights_off",
                                                        "groupName": "lights"},
                                                       {"id": 2699919, "groupId": 1096003, "name": "stops",
                                                        "groupName": "movement"}]}]}]}, {
                           "meta": {
                               "type": "point", "classId": 1379946, "className": "car",
                               "createdBy": {"email": "arturn@superannotate.com", "role": "Admin"},
                               "createdAt": "2022-05-17T11:40:28.691Z",
                               "updatedBy": {"email": "arturn@superannotate.com", "role": "Admin"},
                               "updatedAt": "2022-05-17T12:02:43.429Z", "start": 2878270,
                               "end": 5084595}, "parameters": [
                               {
                                   "start": 2878270,
                                   "end": 5084595,
                                   "timestamps": [
                                       {
                                           "x": 915.5, "y": 461.21,
                                           "timestamp": 2878270,
                                           "attributes": [
                                               {"id": 2699918,
                                                "groupId": 1096003,
                                                "name": "goes",
                                                "groupName": "movement"},
                                               {"id": 2699920,
                                                "groupId": 1096004,
                                                "name": "lights_on",
                                                "groupName": "lights"}]},
                                       {
                                           "x": 915.5, "y": 461.21,
                                           "timestamp": 5084595,
                                           "attributes": [
                                               {"id": 2699918,
                                                "groupId": 1096003,
                                                "name": "goes",
                                                "groupName": "movement"},
                                               {"id": 2699920,
                                                "groupId": 1096004,
                                                "name": "lights_on",
                                                "groupName": "lights"}]}]}]}
                       ],
                   "tags": []}


class TestVideoFrameGenerator(TestCase):
    ANNOTATIONS_PATH = "data_set/video_annotation"

    def test_frame_generator(self):
        generator = VideoFrameGenerator(TEST_SMALL_ANNOTATION, fps=1)
        assert 2 == len([i for i in generator])

    def test_frame_generator_2(self):
        generator = VideoFrameGenerator(TEST_ANNOTATION, fps=1)
        assert 31 == len([i for i in generator])
