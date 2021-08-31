import src.superannotate as sa
import time
#
# s = time.time()
#
# sa.get_project_metadata("dev")
#
# e = time.time()
# print(e-s)
# #
import cProfile
import pstats, io



pr = cProfile.Profile()
pr.enable()

sa.delete_images("dev")
sa.upload_images_from_folder_to_project("dev", "/Users/vaghinak.basentsyan/www/superannotate-python-sdk/tests/data_set/sample_project_vector")

pr.disable()
s = io.StringIO()

ps = pstats.Stats(pr, stream=s)
ps.print_stats()
print(s.getvalue())