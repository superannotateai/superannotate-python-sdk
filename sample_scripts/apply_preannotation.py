import concurrent.futures
from pathlib import Path

import superannotate as sa

sa.init("./b_config.json")

project = "Project "
images = sa.search_images(project, annotation_status="NotStarted")

download_dir = Path("/home/hovnatan/b_work")
already_downloaded = list(download_dir.glob("*___objects.json"))

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    i = 0
    futures = []
    for image in images:
        if download_dir / (image + "___objects.json") in already_downloaded:
            print("Ommitting ", image)
            continue
        futures.append(
            executor.submit(
                sa.download_image_preannotations, project, image, download_dir
            )
        )

    for future in concurrent.futures.as_completed(futures):
        i += 1
        print(i, future.result())

sa.upload_annotations_from_folder_to_project(project, download_dir)
