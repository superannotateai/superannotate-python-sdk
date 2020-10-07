import concurrent.futures
from pathlib import Path

import superannotate as sa

sa.init("./b_config.json")

project = "Project "
images = sa.search_images(project, annotation_status="NotStarted")

download_dir = Path("/home/hovnatan/b_work")
already_downloaded = list(download_dir.glob("*___objects.json"))

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = []
    for image in images:
        if download_dir / (image + "___objects.json") in already_downloaded:
            continue
        futures.append(
            executor.submit(
                sa.download_image_preannotations, project, image, download_dir
            )
        )

    for future in concurrent.futures.as_completed(futures):
        print(future.result())
