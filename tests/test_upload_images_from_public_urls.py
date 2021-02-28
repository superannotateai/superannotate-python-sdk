from pathlib import Path

import superannotate as sa


def test_upload_images_from_public_urls_to_project():
    PROJECT_NAME = 'test_public_links_upload1'

    test_img_list = [
        'https://images.pexels.com/photos/3702354/pexels-photo-3702354.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940',
        'https://www.pexels.com/photo/5450829/download/',
        'https://www.pexels.com/photo/3702354/download/',
        'https://www.pexels.com/photo/3702354/download/',
        'https://www.pexels.com/photo/3702354/dwnload/', '', 'test_non_url'
    ]

    if sa.search_projects(PROJECT_NAME) != []:
        sa.delete_project(PROJECT_NAME)
    proj_data = sa.create_project(PROJECT_NAME, "test", "Vector")
    uploaded_urls, uploaded_filenames, duplicate_filenames, not_uploaded_urls = sa.upload_images_from_public_urls_to_project(
        proj_data,
        test_img_list,
        annotation_status='InProgress',
        image_quality_in_editor="original"
    )
    images_in_project = sa.search_images(
        proj_data, annotation_status='InProgress'
    )
    # check how many images were uploaded and how many were not
    assert len(uploaded_urls) == 3
    assert len(duplicate_filenames) == 1
    assert len(uploaded_filenames) == 3
    assert len(not_uploaded_urls) == 3

    for image in images_in_project:
        assert image in uploaded_filenames


def test_upload_images_from_public_to_project_with_image_name():
    PROJECT_NAME = 'test_public_links_upload2'

    test_img_list = [
        'https://images.pexels.com/photos/3702354/pexels-photo-3702354.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940',
        'https://images.pexels.com/photos/3702354/pexels-photo-3702354.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940',
        'https://images.pexels.com/photos/3702354/pexels-photo-3702354.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940',
        'https://images.pexels.com/photos/3702354/pexels-photo-3702354.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940',
        'https://images.pexels.com/photos/3702354/pexels-photo-3702354.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940'
    ]

    img_name_list = ['img1.jpg', 'img2.jpg', 'img3.jpg', 'img4.jpg', 'img5.jpg']

    if sa.search_projects(PROJECT_NAME) != []:
        sa.delete_project(PROJECT_NAME)

    proj_data = sa.create_project(PROJECT_NAME, "test", "Vector")
    uploaded_urls, uploaded_filenames, duplicate_filenames, not_uploaded_urls = sa.upload_images_from_public_urls_to_project(
        proj_data,
        test_img_list,
        img_name_list,
        annotation_status='InProgress',
        image_quality_in_editor="original"
    )
    images_in_project = sa.search_images(
        proj_data, annotation_status='InProgress'
    )
    # check how many images were uploaded and how many were not
    assert len(uploaded_urls) == 5
    assert len(duplicate_filenames) == 0
    assert len(uploaded_filenames) == 5
    assert len(not_uploaded_urls) == 0
