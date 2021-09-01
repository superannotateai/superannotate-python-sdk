import src.superannotate as sa

import cProfile
import pstats
import io
sa.delete_images("dev")


sa.upload_images_from_folder_to_project("dev", "/Users/vaghinak.basentsyan/www/superannotate-python-sdk/tests/data_set/sample_project_vector")
pr = cProfile.Profile()
pr.enable()

sa.upload_annotations_from_folder_to_project("dev", "/Users/vaghinak.basentsyan/www/superannotate-python-sdk/tests/data_set/sample_project_vector")

pr.disable()
s = io.StringIO()

ps = pstats.Stats(pr, stream=s)
ps.print_stats()
print(s.getvalue())