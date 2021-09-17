import os
from os.path import dirname
import src.superannotate as sa
from tests.integration.base import BaseTestCase
from src.superannotate.lib.core import LIMITED_FUNCTIONS
from src.superannotate.lib.core import DEPRICATED_DOCUMENT_VIDEO_MESSAGE
from src.superannotate.lib.core import ProjectType

class TestDepricatedFunctions(BaseTestCase):
    PROJECT_NAME = "document proj 11"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Document"
    PATH_TO_URLS = "data_set/attach_urls.csv"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    TEST_FOLDER_VIDEO_EXPORT_PATH = "data_set/sample_video_text_export"
    UPLOAD_IMAGE_NAME = "6022a74b5384c50017c366cv"
    PROJECT_NAME_2 = "second project"
    PROJECT_DESCRIPTION_2 = "second project"
    PROJECT_TYPE_2 = "Vector"
    EXCEPTION_MESSAGE = LIMITED_FUNCTIONS[ProjectType.DOCUMENT.value]
    EXCEPTION_MESSAGE_DOCUMENT_VIDEO = DEPRICATED_DOCUMENT_VIDEO_MESSAGE


    def setUp(self, *args, **kwargs):
        self.tearDown()

        sa.create_project(
            self.PROJECT_NAME, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE
        )

        sa.create_project(
            self.PROJECT_NAME_2, self.PROJECT_DESCRIPTION_2, self.PROJECT_TYPE_2
        )

    def tearDown(self) -> None:
        projects = sa.search_projects(self.PROJECT_NAME, return_metadata=True)
        for project in projects:
            sa.delete_project(project)

        projects = sa.search_projects(self.PROJECT_NAME_2, return_metadata=True)
        for project in projects:
            sa.delete_project(project)

    @property
    def video_export_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_VIDEO_EXPORT_PATH)

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @property
    def annotation_path(self):
        return f'{self.folder_path}/example_image_1.jpg___objects.json'

    @property
    def image_path(self):
        return f'{self.folder_path}/example_image_1.jpg'


    def test_depricated_functions(self):
        _, _, _ = sa.attach_document_urls_to_project(
            self.PROJECT_NAME,
            os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS),
        )
        msg = ""
        try:
            msg = ""
            sa.upload_images_from_folder_to_project(self.PROJECT_NAME,"some")
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.get_image_metadata(self.PROJECT_NAME,"some")
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.search_images(self.PROJECT_NAME)
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.upload_images_to_project(self.PROJECT_NAME,["some"])
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.upload_annotations_from_folder_to_project(self.PROJECT_NAME,"some")
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.upload_image_annotations(self.PROJECT_NAME,"some",self.annotation_path)
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.download_image(self.PROJECT_NAME,self.UPLOAD_IMAGE_NAME,'./')
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.download_image_annotations(self.PROJECT_NAME,self.UPLOAD_IMAGE_NAME,"./")
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.get_image_annotations(self.PROJECT_NAME,self.UPLOAD_IMAGE_NAME)
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.set_image_annotation_status(self.PROJECT_NAME,self.UPLOAD_IMAGE_NAME,"Completed")
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.attach_image_urls_to_project(
                self.PROJECT_NAME,
                os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS),
            )
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.clone_project(self.PROJECT_NAME_2,self.PROJECT_NAME)
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.copy_image(self.PROJECT_NAME,self.UPLOAD_IMAGE_NAME,self.PROJECT_NAME_2)
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.upload_images_to_project(self.PROJECT_NAME,[self.image_path,])
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.upload_video_to_project(self.PROJECT_NAME,"some path")
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.add_annotation_bbox_to_image(self.PROJECT_NAME, self.UPLOAD_IMAGE_NAME, [1,2,3,4] , "some class")
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.delete_images(self.PROJECT_NAME, [self.UPLOAD_IMAGE_NAME])
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.get_project_image_count(self.PROJECT_NAME)
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.set_project_workflow(self.PROJECT_NAME, [{}])
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.upload_preannotations_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.add_annotation_comment_to_image(self.PROJECT_NAME, self.UPLOAD_IMAGE_NAME,"some comment",[1,2],"some user")
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.add_annotation_point_to_image(self.PROJECT_NAME, self.UPLOAD_IMAGE_NAME,[1,2],"some class")
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.consensus(self.PROJECT_NAME, ["some"], self.video_export_path)
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE_DOCUMENT_VIDEO, msg)
        try:
            msg = ""
            sa.copy_images(self.PROJECT_NAME, [self.UPLOAD_IMAGE_NAME], self.PROJECT_NAME_2)
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.get_project_workflow(self.PROJECT_NAME)
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.move_image(self.PROJECT_NAME,self.UPLOAD_IMAGE_NAME, self.PROJECT_NAME_2)
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.move_images(self.PROJECT_NAME,[self.UPLOAD_IMAGE_NAME], self.PROJECT_NAME_2)
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.set_images_annotation_statuses(self.PROJECT_NAME,"Completed",[self.UPLOAD_IMAGE_NAME])
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.class_distribution(self.video_export_path, [self.PROJECT_NAME])
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE_DOCUMENT_VIDEO, msg)
        try:
            msg = ""
            sa.convert_project_type(self.video_export_path,"./")
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE_DOCUMENT_VIDEO, msg)
        try:
            msg = ""
            sa.prepare_export(self.PROJECT_NAME,include_fuse=True,only_pinned=True)
        except Exception as e:
            msg = str(e)
        self.assertIn("Include fuse functionality is not supported", msg)
        try:
            msg = ""
            sa.attach_video_urls_to_project(
                self.PROJECT_NAME,
                os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS),
            )
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.benchmark(self.PROJECT_NAME, "some", ["some folder1"])
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)
        try:
            msg = ""
            sa.upload_videos_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
        except Exception as e:
            msg = str(e)
        self.assertIn(self.EXCEPTION_MESSAGE, msg)


        # TODO: need feedback
        # try:
        #     msg = ""
        #     sa.export_annotation(
        #         "input_dir", "fromSuperAnnotate/panoptic_test", "COCO", "panoptic_test", "Pixel",
        #         "panoptic_segmentation"
        #     )
        # except Exception as e:
        #     msg = str(e)
        # self.assertIn(self.EXCEPTION_MESSAGE, msg)
        # TODO: returns None for not existing contributer
        # try:
        #     msg = ""
        #     sa.assign_images(self.PROJECT_NAME,[self.UPLOAD_IMAGE_NAME],"some user")
        # except Exception as e:
        #     msg = str(e)
        # self.assertIn(self.EXCEPTION_MESSAGE, msg)
        # TODO: image quality error
        # try:
        #     msg = ""
        #     sa.set_project_default_image_quality_in_editor(self.PROJECT_NAME,"original")
        # except Exception as e:
        #     msg = str(e)
        # self.assertIn(self.EXCEPTION_MESSAGE, msg)









