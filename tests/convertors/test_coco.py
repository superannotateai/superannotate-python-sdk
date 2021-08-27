# TODO refactor
# from pathlib import Path
#
# import superannotate as sa
#
# from ..common import upload_project
#
#
# def test_coco_vector_instance(tmpdir):
#     project_name = "coco2sa_vector_instance"
#
#     input_dir = Path(
#         "tests"
#     ) / "converter_test" / "COCO" / "input" / "toSuperAnnotate" / "instance_segmentation"
#     out_dir = Path(tmpdir) / project_name
#     sa.import_annotation(
#         input_dir, out_dir, "COCO", "instances_test", "Vector",
#         "instance_segmentation"
#     )
#
#     description = 'coco vector instance segmentation'
#     ptype = 'Vector'
#     upload_project(out_dir, project_name, description, ptype)
#
#
# def test_coco_vector_object(tmpdir):
#     project_name = "coco2sa_vector_object"
#
#     input_dir = Path(
#         "tests"
#     ) / "converter_test" / "COCO" / "input" / "toSuperAnnotate" / "instance_segmentation"
#     out_dir = Path(tmpdir) / project_name
#     sa.import_annotation(
#         input_dir, out_dir, "COCO", "instances_test", "Vector",
#         "object_detection"
#     )
#
#     description = 'coco vector object detection'
#     ptype = 'Vector'
#     upload_project(out_dir, project_name, description, ptype)
#
#
# def test_coco_vector_keypoint(tmpdir):
#     project_name = "coco2sa_keypoint"
#
#     input_dir = Path(
#         "tests"
#     ) / "converter_test" / "COCO" / "input" / "toSuperAnnotate" / "keypoint_detection/"
#     out_dir = Path(tmpdir) / project_name
#     sa.import_annotation(
#         input_dir, out_dir, "COCO", "person_keypoints_test", "Vector",
#         "keypoint_detection"
#     )
#
#     description = 'coco vector keypoint detection'
#     ptype = 'Vector'
#     upload_project(out_dir, project_name, description, ptype)
#
#
# def test_coco_panoptic(tmpdir):
#     project_name = "coco2sa_panoptic"
#
#     input_dir = Path(
#         "tests"
#     ) / "converter_test" / "COCO" / "input" / "toSuperAnnotate" / "panoptic_segmentation"
#     out_dir = Path(tmpdir) / project_name
#     sa.import_annotation(
#         input_dir, out_dir, "COCO", "panoptic_test", "Pixel",
#         "panoptic_segmentation"
#     )
#
#     description = 'coco pixel panoptic segmentation'
#     ptype = 'Pixel'
#     upload_project(out_dir, project_name, description, ptype)
#
#
# def test_coco_pixel_instance(tmpdir):
#     project_name = "coco2sa_pixel_instance"
#
#     input_dir = Path(
#         "tests"
#     ) / "converter_test" / "COCO" / "input" / "toSuperAnnotate" / "instance_segmentation"
#     out_dir = Path(tmpdir) / project_name
#     sa.import_annotation(
#         input_dir, out_dir, "COCO", "instances_test", "Pixel",
#         "instance_segmentation"
#     )
#
#     description = 'coco pixel instance segmentation'
#     ptype = 'Pixel'
#     upload_project(out_dir, project_name, description, ptype)
#
#
# def test_sa_to_coco_to_sa(tmpdir):
#     input_dir = Path("tests") / "sample_project_pixel"
#     output1 = Path(tmpdir) / 'to_coco'
#     output2 = Path(tmpdir) / 'to_sa'
#
#     sa.export_annotation(
#         input_dir, output1, "COCO", "object_test", "Pixel",
#         "instance_segmentation"
#     )
#
#     sa.import_annotation(
#         output1, output2, "COCO", "object_test", "Pixel",
#         "instance_segmentation", 'image_set'
#     )
#
#     project_name = 'coco_pipeline_new'
#     description = 'test_instane'
#     ptype = 'Pixel'
#     upload_project(output2, project_name, description, ptype)
