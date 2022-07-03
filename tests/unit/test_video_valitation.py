from unittest import TestCase

from src.superannotate import SAClient

sa = SAClient()
PAYLOAD = {
    "metadata": {
        "name": "video_file_example_1",
        "duration": 30526667,
        "width": 1920,
        "height": 1080,
        "lastAction": {
            "timestamp": 1656499500695,
            "email": "arturn@superannotate.com"
        },
        "projectId": 202655,
        "url": "https://sa-public-files.s3.us-west-2.amazonaws.com/Video+project/video_file_example_1.mp4",
        "status": "InProgress",
        "error": None,
        "annotatorEmail": None,
        "qaEmail": None
    },
    "instances": [
        {
            "meta": {
                "type": "bbox",
                "classId": 1379945,
                "className": "tree",
                "start": 0,
                "end": 2515879,
                "createdBy": {
                    "email": "arturn@superannotate.com",
                    "role": "Admin"
                },
                "createdAt": "2022-03-02T12:23:10.887Z",
                "updatedBy": {
                    "email": "arturn@superannotate.com",
                    "role": "Admin"
                },
                "updatedAt": "2022-05-17T13:30:11.963Z",
                "pointLabels": {}
            },
            "parameters": [
                {
                    "start": 0,
                    "end": 2515879,
                    "timestamps": [
                        {
                            "points": {
                                "x1": 496.13,
                                "y1": 132.02,
                                "x2": 898.05,
                                "y2": 515.25
                            },
                            "timestamp": 0,
                            "attributes": [
                                {
                                    "id": 2699916,
                                    "groupId": 1096002,
                                    "name": "standing",
                                    "groupName": "state"
                                }
                            ]
                        },
                        {
                            "points": {
                                "x1": 744.37,
                                "y1": 66.41,
                                "x2": 1146.29,
                                "y2": 449.64
                            },
                            "timestamp": 640917,
                            "attributes": [
                                {
                                    "id": 2699917,
                                    "groupId": 1096002,
                                    "name": "falling",
                                    "groupName": "state"
                                }
                            ]
                        },
                        {
                            "points": {
                                "x1": 857.56,
                                "y1": 227.21,
                                "x2": 1259.48,
                                "y2": 610.44
                            },
                            "timestamp": 1215864,
                            "attributes": [
                                {
                                    "id": 2699916,
                                    "groupId": 1096002,
                                    "name": "standing",
                                    "groupName": "state"
                                }
                            ]
                        },
                        {
                            "points": {
                                "x1": 857.56,
                                "y1": 227.21,
                                "x2": 1259.48,
                                "y2": 610.44
                            },
                            "timestamp": 1573648,
                            "attributes": [
                                {
                                    "id": 2699917,
                                    "groupId": 1096002,
                                    "name": "falling",
                                    "groupName": "state"
                                }
                            ]
                        },
                        {
                            "points": {
                                "x1": 1038.3,
                                "y1": 270.54,
                                "x2": 1440.22,
                                "y2": 653.77
                            },
                            "timestamp": 2255379,
                            "attributes": [
                                {
                                    "id": 2699917,
                                    "groupId": 1096002,
                                    "name": "falling",
                                    "groupName": "state"
                                }
                            ]
                        },
                        {
                            "points": {
                                "x1": 1038.3,
                                "y1": 270.54,
                                "x2": 1440.22,
                                "y2": 653.77
                            },
                            "timestamp": 2515879,
                            "attributes": [
                                {
                                    "id": 2699917,
                                    "groupId": 1096002,
                                    "name": "falling",
                                    "groupName": "state"
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "meta": {
                "type": "bbox",
                "classId": 1379945,
                "className": "tree",
                "start": 2790828,
                "end": 5068924,
                "createdBy": {
                    "email": "arturn@superannotate.com",
                    "role": "Admin"
                },
                "createdAt": "2022-03-02T12:36:52.126Z",
                "updatedBy": {
                    "email": "arturn@superannotate.com",
                    "role": "Admin"
                },
                "updatedAt": "2022-03-02T12:38:24.056Z",
                "pointLabels": {}
            },
            "parameters": [
                {
                    "start": 2790828,
                    "end": 5068924,
                    "timestamps": [
                        {
                            "points": {
                                "x1": 507.3,
                                "y1": 569.55,
                                "x2": 979.58,
                                "y2": 965.84
                            },
                            "timestamp": 2790828,
                            "attributes": []
                        },
                        {
                            "points": {
                                "x1": 507.3,
                                "y1": 569.55,
                                "x2": 979.58,
                                "y2": 965.84
                            },
                            "timestamp": 2888183,
                            "attributes": [
                                {
                                    "id": 2699917,
                                    "groupId": 1096002,
                                    "name": "falling",
                                    "groupName": "state"
                                }
                            ]
                        },
                        {
                            "points": {
                                "x1": 507.3,
                                "y1": 569.55,
                                "x2": 979.58,
                                "y2": 965.84
                            },
                            "timestamp": 5068924,
                            "attributes": [
                                {
                                    "id": 2699917,
                                    "groupId": 1096002,
                                    "name": "falling",
                                    "groupName": "state"
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "meta": {
                "type": "bbox",
                "classId": 1379946,
                "className": "car",
                "start": 4502645,
                "end": 6723950,
                "createdBy": {
                    "email": "arturn@superannotate.com",
                    "role": "Admin"
                },
                "createdAt": "2022-03-02T12:39:19.970Z",
                "updatedBy": {
                    "email": "arturn@superannotate.com",
                    "role": "Admin"
                },
                "updatedAt": "2022-03-02T12:41:13.536Z",
                "pointLabels": {}
            },
            "parameters": [
                {
                    "start": 4502645,
                    "end": 6723950,
                    "timestamps": [
                        {
                            "points": {
                                "x1": 792.08,
                                "y1": 671.23,
                                "x2": 1178.97,
                                "y2": 987.47
                            },
                            "timestamp": 4502645,
                            "attributes": []
                        },
                        {
                            "points": {
                                "x1": 792.08,
                                "y1": 671.23,
                                "x2": 1178.97,
                                "y2": 987.47
                            },
                            "timestamp": 5330158,
                            "attributes": [
                                {
                                    "id": 2699918,
                                    "groupId": 1096003,
                                    "name": "goes",
                                    "groupName": "movement"
                                },
                                {
                                    "id": 2699920,
                                    "groupId": 1096004,
                                    "name": "lights_on",
                                    "groupName": "lights"
                                }
                            ]
                        },
                        {
                            "points": {
                                "x1": 792.08,
                                "y1": 671.23,
                                "x2": 1178.97,
                                "y2": 987.47
                            },
                            "timestamp": 5825043,
                            "attributes": [
                                {
                                    "id": 2699920,
                                    "groupId": 1096004,
                                    "name": "lights_on",
                                    "groupName": "lights"
                                },
                                {
                                    "id": 2699919,
                                    "groupId": 1096003,
                                    "name": "stops",
                                    "groupName": "movement"
                                }
                            ]
                        },
                        {
                            "points": {
                                "x1": 792.08,
                                "y1": 671.23,
                                "x2": 1178.97,
                                "y2": 987.47
                            },
                            "timestamp": 6303703,
                            "attributes": [
                                {
                                    "id": 2699919,
                                    "groupId": 1096003,
                                    "name": "stops",
                                    "groupName": "movement"
                                },
                                {
                                    "id": 2699921,
                                    "groupId": 1096004,
                                    "name": "lights_off",
                                    "groupName": "lights"
                                }
                            ]
                        },
                        {
                            "points": {
                                "x1": 792.08,
                                "y1": 671.23,
                                "x2": 1178.97,
                                "y2": 987.47
                            },
                            "timestamp": 6723950,
                            "attributes": [
                                {
                                    "id": 2699919,
                                    "groupId": 1096003,
                                    "name": "stops",
                                    "groupName": "movement"
                                },
                                {
                                    "id": 2699921,
                                    "groupId": 1096004,
                                    "name": "lights_off",
                                    "groupName": "lights"
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "meta": {
                "type": "event",
                "classId": 1379946,
                "className": "car",
                "start": 1655026,
                "end": 3365220,
                "createdBy": {
                    "email": "arturn@superannotate.com",
                    "role": "Admin"
                },
                "createdAt": "2022-03-02T12:41:39.135Z",
                "updatedBy": {
                    "email": "arturn@superannotate.com",
                    "role": "Admin"
                },
                "updatedAt": "2022-03-02T12:41:39.135Z"
            },
            "parameters": [
                {
                    "start": 1655026,
                    "end": 3365220,
                    "timestamps": [
                        {
                            "timestamp": 1655026,
                            "attributes": []
                        },
                        {
                            "timestamp": 3365220,
                            "attributes": []
                        }
                    ]
                }
            ]
        },
        {
            "meta": {
                "type": "point",
                "classId": 1379946,
                "className": "car",
                "start": 617519,
                "end": 2342388,
                "createdBy": {
                    "email": "arturn@superannotate.com",
                    "role": "Admin"
                },
                "createdAt": "2022-05-17T11:38:50.041Z",
                "updatedBy": {
                    "email": "arturn@superannotate.com",
                    "role": "Admin"
                },
                "updatedAt": "2022-05-17T11:50:57.784Z"
            },
            "parameters": [
                {
                    "start": 617519,
                    "end": 2342388,
                    "timestamps": [
                        {
                            "x": 612.81,
                            "y": 606.79,
                            "timestamp": 617519,
                            "attributes": [
                                {
                                    "id": 2699918,
                                    "groupId": 1096003,
                                    "name": "goes",
                                    "groupName": "movement"
                                },
                                {
                                    "id": 2699920,
                                    "groupId": 1096004,
                                    "name": "lights_on",
                                    "groupName": "lights"
                                }
                            ]
                        },
                        {
                            "x": 653.05,
                            "y": 648.81,
                            "timestamp": 1266439,
                            "attributes": [
                                {
                                    "id": 2699918,
                                    "groupId": 1096003,
                                    "name": "goes",
                                    "groupName": "movement"
                                },
                                {
                                    "id": 2699920,
                                    "groupId": 1096004,
                                    "name": "lights_on",
                                    "groupName": "lights"
                                }
                            ]
                        },
                        {
                            "x": 691.9399999999999,
                            "y": 682.7099999999999,
                            "timestamp": 1569965,
                            "attributes": [
                                {
                                    "id": 2699918,
                                    "groupId": 1096003,
                                    "name": "goes",
                                    "groupName": "movement"
                                },
                                {
                                    "id": 2699921,
                                    "groupId": 1096004,
                                    "name": "lights_off",
                                    "groupName": "lights"
                                }
                            ]
                        },
                        {
                            "x": 691.9399999999999,
                            "y": 682.7099999999999,
                            "timestamp": 2342388,
                            "attributes": [
                                {
                                    "id": 2699921,
                                    "groupId": 1096004,
                                    "name": "lights_off",
                                    "groupName": "lights"
                                },
                                {
                                    "id": 2699919,
                                    "groupId": 1096003,
                                    "name": "stops",
                                    "groupName": "movement"
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "meta": {
                "type": "point",
                "classId": 1379946,
                "className": "car",
                "start": 2878270,
                "end": 5084595,
                "createdBy": {
                    "email": "arturn@superannotate.com",
                    "role": "Admin"
                },
                "createdAt": "2022-05-17T11:40:28.691Z",
                "updatedBy": {
                    "email": "arturn@superannotate.com",
                    "role": "Admin"
                },
                "updatedAt": "2022-05-17T12:02:43.429Z"
            },
            "parameters": [
                {
                    "start": 2878270,
                    "end": 5084595,
                    "timestamps": [
                        {
                            "x": 915.5,
                            "y": 461.21,
                            "timestamp": 2878270,
                            "attributes": [
                                {
                                    "id": 2699918,
                                    "groupId": 1096003,
                                    "name": "goes",
                                    "groupName": "movement"
                                },
                                {
                                    "id": 2699920,
                                    "groupId": 1096004,
                                    "name": "lights_on",
                                    "groupName": "lights"
                                }
                            ]
                        },
                        {
                            "x": 915.5,
                            "y": 461.21,
                            "timestamp": 5084595,
                            "attributes": [
                                {
                                    "id": 2699918,
                                    "groupId": 1096003,
                                    "name": "goes",
                                    "groupName": "movement"
                                },
                                {
                                    "id": 2699920,
                                    "groupId": 1096004,
                                    "name": "lights_on",
                                    "groupName": "lights"
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "meta": {
                "type": "polygon",
                "classId": 1379945,
                "className": "tree",
                "start": 5664421,
                "end": 8368555,
                "createdBy": {
                    "email": "arturn@superannotate.com",
                    "role": "Admin"
                },
                "createdAt": "2022-06-29T10:43:15.995Z",
                "updatedBy": {
                    "email": "arturn@superannotate.com",
                    "role": "Admin"
                },
                "updatedAt": "2022-06-29T10:43:57.540Z"
            },
            "parameters": [
                {
                    "start": 5664421,
                    "end": 8368555,
                    "timestamps": [
                        {
                            "points": [
                                651.25,
                                365.32,
                                855.92,
                                240.26,
                                1017.63,
                                503.6
                            ],
                            "timestamp": 5664421,
                            "attributes": []
                        },
                        {
                            "points": [
                                651.25,
                                365.32,
                                855.92,
                                240.26,
                                1017.63,
                                503.6
                            ],
                            "timestamp": 6496259,
                            "attributes": [
                                {
                                    "id": 2699916,
                                    "groupId": 1096002,
                                    "name": "standing",
                                    "groupName": "state"
                                }
                            ]
                        },
                        {
                            "points": [
                                839.98,
                                358.45,
                                1044.65,
                                233.39,
                                1206.36,
                                496.73
                            ],
                            "timestamp": 6826353,
                            "attributes": [
                                {
                                    "id": 2699916,
                                    "groupId": 1096002,
                                    "name": "standing",
                                    "groupName": "state"
                                }
                            ]
                        },
                        {
                            "points": [
                                839.98,
                                358.45,
                                1044.65,
                                233.39,
                                1206.36,
                                496.73
                            ],
                            "timestamp": 8368555,
                            "attributes": [
                                {
                                    "id": 2699917,
                                    "groupId": 1096002,
                                    "name": "falling",
                                    "groupName": "state"
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "meta": {
                "type": "polyline",
                "classId": 1379945,
                "className": "tree",
                "start": 8754105,
                "end": 11312997,
                "createdBy": {
                    "email": "arturn@superannotate.com",
                    "role": "Admin"
                },
                "createdAt": "2022-06-29T10:44:15.979Z",
                "updatedBy": {
                    "email": "arturn@superannotate.com",
                    "role": "Admin"
                },
                "updatedAt": "2022-06-29T10:45:00.660Z"
            },
            "parameters": [
                {
                    "start": 8754105,
                    "end": 11312997,
                    "timestamps": [
                        {
                            "points": [
                                679.05,
                                412.73,
                                1050.61,
                                484.06,
                                885.75,
                                737.4
                            ],
                            "timestamp": 8754105,
                            "attributes": [
                                {
                                    "id": 2699916,
                                    "groupId": 1096002,
                                    "name": "standing",
                                    "groupName": "state"
                                }
                            ]
                        },
                        {
                            "points": [
                                679.05,
                                412.73,
                                1050.61,
                                484.06,
                                885.75,
                                737.4
                            ],
                            "timestamp": 9467109,
                            "attributes": [
                                {
                                    "id": 2699917,
                                    "groupId": 1096002,
                                    "name": "falling",
                                    "groupName": "state"
                                }
                            ]
                        },
                        {
                            "points": [
                                790.96,
                                292.26,
                                1162.52,
                                363.59,
                                997.66,
                                616.93
                            ],
                            "timestamp": 9757592,
                            "attributes": [
                                {
                                    "id": 2699917,
                                    "groupId": 1096002,
                                    "name": "falling",
                                    "groupName": "state"
                                }
                            ]
                        },
                        {
                            "points": [
                                790.96,
                                292.26,
                                1162.52,
                                363.59,
                                997.66,
                                616.93
                            ],
                            "timestamp": 11312997,
                            "attributes": [
                                {
                                    "id": 2699917,
                                    "groupId": 1096002,
                                    "name": "falling",
                                    "groupName": "state"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ],
    "tags": [
        "tg2",
        "tg1"
    ]
}


class TestVideoValidators(TestCase):

    def test_polygon_polyline(self):
        response = sa.controller.validate_annotations("video", PAYLOAD)
        assert not response.report_messages
