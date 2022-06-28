from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestRecursiveFolderPixel(BaseTestCase):
    PROJECT_NAME = "pixel_recursive_test"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Pixel"
    S3_FOLDER_PATH = "pixel_recursive_annotations"
    JSON_POSTFIX = "*.json"

    def test_recursive_upload_pixel(self):
        uploaded, _, duplicated = sa.upload_images_from_folder_to_project(self.PROJECT_NAME,
                                                                          self.S3_FOLDER_PATH,
                                                                          from_s3_bucket="test-openseadragon-1212",
                                                                          recursive_subfolders=True
                                                                          )

        uploaded, failed, missing = sa.upload_annotations_from_folder_to_project(self.PROJECT_NAME,
                                                                          self.S3_FOLDER_PATH,
                                                                          from_s3_bucket="test-openseadragon-1212",
                                                                          recursive_subfolders=True
                                                                          )
        self.assertEqual(4, len(uploaded))
        self.assertEqual(0, len(failed))
        self.assertEqual(1, len(missing))


