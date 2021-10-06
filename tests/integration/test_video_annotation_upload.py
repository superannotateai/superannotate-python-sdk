import os
import tempfile
import json
from os.path import dirname

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestUploadVideoAnnotation(BaseTestCase):
    PROJECT_NAME = "video annotation upload"
    PATH_TO_URLS = "data_set/attach_video_for_annotation.csv"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Video"
    ANNOTATIONS_PATH = "data_set/video_annotation"
    CLASSES_PATH = "data_set/video_annotation/classes/classes.json"

    @property
    def csv_path(self):
        return os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS)

    @property
    def annotations_path(self):
        return os.path.join(dirname(dirname(__file__)), self.ANNOTATIONS_PATH)

    @property
    def classes_path(self):
        return os.path.join(dirname(dirname(__file__)), self.CLASSES_PATH)


    def test_video_annotation_upload(self):
        sa.create_annotation_classes_from_classes_json(self.PROJECT_NAME, self.classes_path)

        _, _, _ = sa.attach_video_urls_to_project(
            self.PROJECT_NAME,
            self.csv_path,
        )
        sa.upload_annotations_from_folder_to_project(self.PROJECT_NAME, self.annotations_path)
        export = sa.prepare_export(self.PROJECT_NAME)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = temp_dir
            sa.download_export(self.PROJECT_NAME, export, output_path, True)
            classes = sa.search_annotation_classes(self.PROJECT_NAME)
            ids_to_replace = [sa.get_project_metadata(self.PROJECT_NAME)['id']]
            for class_ in classes:
                for attribute_group in class_['attribute_groups']:
                    for attribute in attribute_group['attributes']:
                        ids_to_replace.append(attribute['id'])
                    ids_to_replace.append(attribute_group['id'])
                ids_to_replace.append(class_['id'])
            downloaded_annotation = open(f"{output_path}/video.mp4.json").read()
            for id_ in ids_to_replace:
                downloaded_annotation = downloaded_annotation.replace(str(id_), "0")
            downloaded_annotation = json.loads(downloaded_annotation)
            uploaded_annotation = json.loads(open(f"{self.annotations_path}/video.mp4.json").read().replace("152038","0").replace("859496","0").replace("338357","0").replace("1175876","0"))
            self.assertEqual(downloaded_annotation, uploaded_annotation)





