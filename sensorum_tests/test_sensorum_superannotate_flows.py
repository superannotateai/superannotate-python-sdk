## Manual test of the super annotate servicex
import os
import random
import time

from superannotate import SAClient
from superannotate import enums as SAEnums

try:
    SA_TOKEN = os.environ.get("SA_TOKEN")
except:
    raise (
        "SA_TOKEN not found in environment variables. It must be set to the prod token"
    )

c = SAClient(token=SA_TOKEN)

random_number = random.randint(0, 1000000)
TEST_PROJECT_NAME = f"TEST PROJ - pls delete - {random_number}"

assert len(c.search_projects("Cough")) > 1

assert len(c.search_projects(TEST_PROJECT_NAME)) == 0

c.create_project(
    project_name=TEST_PROJECT_NAME,
    project_description="Test Description",
    project_type="Video",
    classes=[
        {
            "name": "cough",
            "color": "#ff0000",
            "type": SAEnums.ClassTypeEnum.TAG.value,
        },
        {
            "name": "not_cough",
            "color": "#00ff00",
            "type": SAEnums.ClassTypeEnum.TAG.value,
        },
    ],
)

assert len(c.search_projects(TEST_PROJECT_NAME)) == 1

c.create_folder(TEST_PROJECT_NAME, "TEST FOLDER - pls delete")


# search_folders
assert len(c.search_folders(TEST_PROJECT_NAME, "TEST FOLDER - pls delete")) == 1
assert len(c.search_folders(TEST_PROJECT_NAME, "RANDOM")) == 0

# attach_items_from_integrated_storage
c.attach_items_from_integrated_storage(
    project=f"{TEST_PROJECT_NAME}/TEST FOLDER - pls delete",
    integration={"name": "sensorum-dev"},
    folder_path="batch_extraction_2023_05_20_annotation_load_1686861565/",
)


# get_annotations
# wait for 5 seconds for the annotations to be created

print("Waiting for 15 seconds for the annotations to be created")
time.sleep(15)

annotations = c.get_annotations(f"{TEST_PROJECT_NAME}/TEST FOLDER - pls delete")

assert (
    len(annotations) == 853
), f"len(annotations) = {len(annotations)} != 853. annotations = {annotations}"

# there are 853 files in the folder batch_extraction_2023_05_20_annotation_load_1686861565/ in the sensorum-dev superannotaate

real_project = c.search_projects("Cough")[0]
print("real_project", real_project)

assert "Cough".lower() in real_project.lower()

# get_folder_metadata
folder_metadata = c.get_folder_metadata(TEST_PROJECT_NAME, f"TEST FOLDER - pls delete")
print("folder_metadata", folder_metadata)

assert folder_metadata["name"] == "TEST FOLDER - pls delete"

# Delte the project
c.delete_project(TEST_PROJECT_NAME)
