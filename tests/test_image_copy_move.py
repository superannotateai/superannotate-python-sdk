import time
from pathlib import Path

import superannotate as sa
from .test_assign_images import safe_create_project

PROJECT_NAME_CPY = "test image copy 1"
PROJECT_NAME_CPY_MULT = "test image copy mult 2"
PROJECT_NAME_MOVE = "test image move 3"
PROJECT_NAME_CPY_FOLDER = "test image copy folder 4"


def test_image_copy_mult(tmpdir):
    project = safe_create_project(PROJECT_NAME_CPY_MULT)

    sa.upload_image_to_project(
        project,
        "./tests/sample_project_vector/example_image_1.jpg",
        annotation_status="InProgress"
    )
    sa.create_annotation_classes_from_classes_json(
        project, "./tests/sample_project_vector/classes/classes.json"
    )
    time.sleep(2)
    sa.upload_image_annotations(
        project, "example_image_1.jpg",
        "./tests/sample_project_vector/example_image_1.jpg___objects.json"
    )
    sa.upload_image_to_project(
        project,
        "./tests/sample_project_vector/example_image_2.jpg",
        annotation_status="InProgress"
    )
    time.sleep(2)
    sa.pin_image(project, "example_image_1.jpg")
    time.sleep(2)
    images = sa.search_images(project)
    assert len(images) == 2
    image = images[0]

    for _ in range(3):
        sa.copy_image(
            project,
            image,
            project,
            include_annotations=True,
            copy_annotation_status=True,
            copy_pin=True
        )
    time.sleep(2)
    assert len(sa.search_images(project)) == 5
    images = sa.search_images(project)
    for i in range(3):
        assert f"example_image_1_({i+1}).jpg" in images
    anns = sa.get_image_annotations(project, f"example_image_1_({i+1}).jpg")
    assert anns["annotation_json"] is not None

    metadata = sa.get_image_metadata(project, f"example_image_1_({i+1}).jpg")
    assert metadata["is_pinned"] == 1


def test_image_copy(tmpdir):
    project = safe_create_project(PROJECT_NAME_CPY)

    sa.upload_image_to_project(
        project,
        "./tests/sample_project_vector/example_image_1.jpg",
        annotation_status="InProgress"
    )
    sa.upload_image_to_project(
        project,
        "./tests/sample_project_vector/example_image_2.jpg",
        annotation_status="InProgress"
    )

    time.sleep(2)

    images = sa.search_images(project)
    assert len(images) == 2
    image = images[0]

    sa.copy_image(project, image, project)
    time.sleep(2)
    images = sa.search_images(project)
    assert len(images) == 3

    image = "example_image_1_(1).jpg"
    assert len(sa.search_images(project, image)) == 1
    sa.copy_image(project, image, project)
    time.sleep(2)

    image = "example_image_1_(2).jpg"
    assert len(sa.search_images(project, image)) == 1

    projects_found = sa.search_projects(
        PROJECT_NAME_CPY + "dif", return_metadata=True
    )
    for pr in projects_found:
        sa.delete_project(pr)

    time.sleep(2)
    dest_project = sa.create_project(PROJECT_NAME_CPY + "dif", "test", "Vector")
    time.sleep(2)
    sa.copy_image(project, image, dest_project)
    time.sleep(2)
    di = sa.search_images(dest_project, image)
    assert len(di) == 1
    assert di[0] == image


def test_image_move(tmpdir):
    project = safe_create_project(PROJECT_NAME_MOVE)

    sa.upload_image_to_project(
        project,
        "./tests/sample_project_vector/example_image_1.jpg",
        annotation_status="InProgress"
    )
    sa.upload_image_to_project(
        project,
        "./tests/sample_project_vector/example_image_2.jpg",
        annotation_status="InProgress"
    )
    time.sleep(2)

    images = sa.search_images(project)
    assert len(images) == 2
    image = images[0]
    try:
        sa.move_image(project, image, project)
        time.sleep(2)
    except sa.SABaseException as e:
        assert e.message == "Cannot move image if source_project == destination_project."
    else:
        assert False

    projects_found = sa.search_projects(
        PROJECT_NAME_MOVE + "dif", return_metadata=True
    )
    for pr in projects_found:
        sa.delete_project(pr)

    time.sleep(2)

    dest_project = sa.create_project(
        PROJECT_NAME_MOVE + "dif", "test", "Vector"
    )
    time.sleep(2)
    sa.move_image(project, image, dest_project)
    time.sleep(2)
    di = sa.search_images(dest_project, image)
    assert len(di) == 1
    assert di[0] == image

    si = sa.search_images(project, image)
    assert len(si) == 0

    si = sa.search_images(project)
    assert len(si) == 1


# def test_image_copy_folders(tmpdir):
#     tmpdir = Path(tmpdir)

#     projects_found = sa.search_projects(
#         PROJECT_NAME_CPY_FOLDER, return_metadata=True
#     )
#     for pr in projects_found:
#         sa.delete_project(pr)

#     project = sa.create_project(PROJECT_NAME_CPY_FOLDER, "test", "Vector")

#     sa.upload_image_to_project(
#         project,
#         "./tests/sample_project_vector/example_image_1.jpg",
#         annotation_status="InProgress"
#     )
#     sa.upload_image_to_project(
#         project,
#         "./tests/sample_project_vector/example_image_2.jpg",
#         annotation_status="InProgress"
#     )

#     sa.create_folder(project, "folder1")

#     sa.copy_image(
#         project, ["example_image_1.jpg", "example_image_2.jpg"],
#         project["name"] + "/folder1"
#     )
#     sa.copy_image(
#         project, ["example_image_1.jpg", "example_image_2.jpg"],
#         project["name"] + "/folder1"
#     )
