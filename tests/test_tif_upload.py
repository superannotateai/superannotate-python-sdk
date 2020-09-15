from pathlib import Path
import filecmp

import pytest

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

PROJECT_NAME = "test_tif"
PROJECT_NAME_LOW_QUALITY = "test_tif_loq"

PROJECT_NAME_S3 = "test_tif_s3"
PROJECT_NAME_LOW_QUALITY_S3 = "test_tif_loq_s3"
S3_BUCKET = "hovnatan-test"


def test_tif_upload(tmpdir):
    tmpdir = Path(tmpdir)
    projects_found = sa.search_projects(PROJECT_NAME)
    for pr in projects_found:
        sa.delete_project(pr)
    project = sa.create_project(PROJECT_NAME, "gg", "Vector")
    sa.upload_images_from_folder_to_project(
        project,
        "sample_tif_files/",
        extensions=["tif"],
        annotation_status="QualityCheck",
        image_quality_in_editor=100
    )
    sa.create_annotation_class(project, "tt", "#FFAAFF")
    image = sa.search_images(project)[0]
    sa.add_annotation_bbox_to_image(project, image, [10, 10, 100, 100], "tt")
    Path(tmpdir / "q100" / "lores").mkdir(parents=True)
    sa.download_image_annotations(project, image, tmpdir / "q100")
    sa.download_image(project, image, tmpdir / "q100", variant='original')
    assert filecmp.cmp(
        f"sample_tif_files/{image['name']}",
        f"{tmpdir}/q100/{image['name']}",
        shallow=False
    )
    sa.download_image(project, image, tmpdir / "q100/lores", variant='lores')
    export = sa.prepare_export(project, include_fuse=True)
    (tmpdir / "q100" / "export").mkdir(parents=True)
    sa.download_export(export, tmpdir / "q100" / "export")
    assert filecmp.cmp(
        f"sample_tif_files/{image['name']}",
        f"{tmpdir}/q100/export/{image['name']}",
        shallow=False
    )

    projects_found = sa.search_projects(PROJECT_NAME_LOW_QUALITY)
    for pr in projects_found:
        sa.delete_project(pr)
    project = sa.create_project(PROJECT_NAME_LOW_QUALITY, "gg", "Vector")
    sa.upload_images_from_folder_to_project(
        project,
        "sample_tif_files/",
        extensions=["tif"],
        annotation_status="QualityCheck",
        image_quality_in_editor=60
    )
    sa.create_annotation_class(project, "tt", "#FFAAFF")
    image = sa.search_images(project)[0]
    sa.add_annotation_bbox_to_image(project, image, [10, 10, 100, 100], "tt")
    Path(tmpdir / "q60" / "lores").mkdir(parents=True)
    sa.download_image_annotations(project, image, tmpdir / "q60")
    sa.download_image(image, tmpdir / "q60", variant='original')
    assert filecmp.cmp(
        f"sample_tif_files/{image['name']}",
        f"{tmpdir}/q60/{image['name']}",
        shallow=False
    )

    sa.download_image(image, tmpdir / "q60/lores", variant='lores')
    export = sa.prepare_export(project, include_fuse=True)
    (tmpdir / "q60" / "export").mkdir(parents=True)
    sa.download_export(export, tmpdir / "q60" / "export")
    assert filecmp.cmp(
        f"sample_tif_files/{image['name']}",
        f"{tmpdir}/q60/export/{image['name']}",
        shallow=False
    )


# def test_tif_upload_s3(tmpdir):
#     tmpdir = Path(tmpdir)
#     projects_found = sa.search_projects(PROJECT_NAME_S3)
#     for pr in projects_found:
#         sa.delete_project(pr)
#     project = sa.create_project(PROJECT_NAME_S3, "gg", "Vector")
#     sa.upload_images_from_folder_to_project(
#         project,
#         "sample_tif_files/",
#         extensions=["tif"],
#         annotation_status="QualityCheck",
#         from_s3_bucket=S3_BUCKET,
#         image_quality_in_editor=100
#     )
#     sa.create_annotation_class(project, "tt", "#FFAAFF")
#     image = sa.search_images(project)[0]
#     sa.add_image_annotation_bbox(image, [10, 10, 100, 100], "tt")
#     Path(tmpdir / "q100" / "lores").mkdir(parents=True)
#     sa.download_image_annotations(image, tmpdir / "q100")
#     sa.download_image(image, tmpdir / "q100", variant='original')
#     assert filecmp.cmp(
#         f"sample_tif_files/{image['name']}",
#         f"{tmpdir}/q100/{image['name']}",
#         shallow=False
#     )
#     sa.download_image(image, tmpdir / "q100/lores", variant='lores')
#     export = sa.prepare_export(project, include_fuse=True)
#     (tmpdir / "q100" / "export").mkdir(parents=True)
#     sa.download_export(export, tmpdir / "q100" / "export")
#     assert filecmp.cmp(
#         f"sample_tif_files/{image['name']}",
#         f"{tmpdir}/q100/export/{image['name']}",
#         shallow=False
#     )

#     projects_found = sa.search_projects(PROJECT_NAME_LOW_QUALITY_S3)
#     for pr in projects_found:
#         sa.delete_project(pr)
#     project = sa.create_project(PROJECT_NAME_LOW_QUALITY_S3, "gg", "Vector")
#     sa.upload_images_from_folder_to_project(
#         project,
#         "sample_tif_files/",
#         extensions=["tif"],
#         annotation_status="QualityCheck",
#         from_s3_bucket=S3_BUCKET,
#         image_quality_in_editor=60
#     )
#     sa.create_annotation_class(project, "tt", "#FFAAFF")
#     image = sa.search_images(project)[0]
#     sa.add_image_annotation_bbox(image, [10, 10, 100, 100], "tt")
#     Path(tmpdir / "q60" / "lores").mkdir(parents=True)
#     sa.download_image_annotations(image, tmpdir / "q60")
#     sa.download_image(image, tmpdir / "q60", variant='original')
#     assert filecmp.cmp(
#         f"sample_tif_files/{image['name']}",
#         f"{tmpdir}/q60/{image['name']}",
#         shallow=False
#     )

#     sa.download_image(image, tmpdir / "q60/lores", variant='lores')
#     export = sa.prepare_export(project, include_fuse=True)
#     (tmpdir / "q60" / "export").mkdir(parents=True)
#     sa.download_export(export, tmpdir / "q60" / "export")
#     assert filecmp.cmp(
#         f"sample_tif_files/{image['name']}",
#         f"{tmpdir}/q60/export/{image['name']}",
#         shallow=False
#     )
