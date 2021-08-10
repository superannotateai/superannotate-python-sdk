import time

import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase


class TestUploadImageFromPublicUrls(BaseTestCase):
    PROJECT_NAME = "test_public_links_upload"
    PROJECT_TYPE = "Vector"
    TEST_IMAGE_LIST_1 = [
        "https://images.pexels.com/photos/3702354/pexels-photo-3702354.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
        "https://www.pexels.com/photo/5450829/download/",
        "https://www.pexels.com/photo/3702354/download/",
        "https://www.pexels.com/photo/3702354/download/",
        "https://www.pexels.com/photo/3702354/dwnload/",
        "",
        "test_non_url",
    ]
    TEST_IMAGE_LIST_2 = [
        "https://images.pexels.com/photos/3702354/pexels-photo-3702354."
        "jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=941",
        "https://images.pexels.com/photos/3702354/pexels-photo-3702354."
        "jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=942",
        "https://images.pexels.com/photos/3702354/pexels-photo-3702354."
        "jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=943",
        "https://images.pexels.com/photos/3702354/pexels-photo-3702354."
        "jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=944",
        "https://images.pexels.com/photos/3702354/pexels-photo-3702354."
        "jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=945",
    ]

    def test_upload_images_from_public_urls_to_project(self):
        (
            uploaded_urls,
            uploaded_filenames,
            duplicate_filenames,
            not_uploaded_urls,
        ) = sa.upload_images_from_public_urls_to_project(
            self.PROJECT_NAME,
            self.TEST_IMAGE_LIST_1,
            annotation_status="InProgress",
            image_quality_in_editor="original",
        )
        time.sleep(3)
        images_in_project = sa.search_images(
            self.PROJECT_NAME, annotation_status="InProgress"
        )
        # check how many images were uploaded and how many were not
        self.assertEqual(len(uploaded_urls), 3)
        self.assertEqual(len(duplicate_filenames), 1)
        self.assertEqual(len(uploaded_filenames), 3)
        self.assertEqual(len(not_uploaded_urls), 3)

        for image in images_in_project:
            self.assertIn(image, uploaded_filenames)

    def test_upload_images_from_public_to_project_with_image_name(self):
        img_name_list = ["img1.jpg", "img2.jpg", "img3.jpg", "img4.jpg", "img5.jpg"]

        (
            uploaded_urls,
            uploaded_filenames,
            duplicate_filenames,
            not_uploaded_urls,
        ) = sa.upload_images_from_public_urls_to_project(
            self.PROJECT_NAME,
            self.TEST_IMAGE_LIST_2,
            img_name_list,
            annotation_status="InProgress",
            image_quality_in_editor="original",
        )
        # images_in_project = sa.search_images(self.PROJECT_NAME, annotation_status="InProgress")
        # check how many images were uploaded and how many were not
        self.assertEqual(len(uploaded_urls), 5)
        self.assertEqual(len(duplicate_filenames), 0)
        self.assertEqual(len(uploaded_filenames), 5)
        self.assertEqual(len(not_uploaded_urls), 0)
