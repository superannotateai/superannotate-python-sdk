import src.superannotate as sa

import cProfile
import pstats
import io
#
# pr = cProfile.Profile()
# pr.enable()
# sa.delete_images("dev")
# sa.upload_images_from_folder_to_project("dev", "/Users/vaghinak.basentsyan/www/superannotate-python-sdk/tests/data_set/sample_project_vector")
# sa.upload_annotations_from_folder_to_project("dev", "/Users/vaghinak.basentsyan/www/superannotate-python-sdk/tests/data_set/sample_project_vector")
#
# pr.disable()
# s = io.StringIO()
#
# ps = pstats.Stats(pr, stream=s)
# ps.print_stats()
# print(s.getvalue())


# import time
# results = []
#
# for i in range(10):
#     start = time.time()
#     sa.delete_images("dev", None)
#     sa.upload_images_from_folder_to_project("dev", "/Users/vaghinak.basentsyan/www/superannotate-python-sdk/tests/data_set/sample_project_vector")
#     sa.upload_annotations_from_folder_to_project("dev", "/Users/vaghinak.basentsyan/www/superannotate-python-sdk/tests/data_set/sample_project_vector")
#     end = time.time()
#     results.append(end-start)
#
# print(results)
# print(sum(results)/10)

# import time
# results = []
# projects = "11", "22", "33", "44", "55", "66", "77", "88", "99"
#
# for project in projects:
#     start = time.time()
#     sa.search_annotation_classes(project)
#     end = time.time()
#     results.append(end-start)
#
# print(results)
# print(sum(results)/9)

print(sa.search_images("Vector/for sdk"))
