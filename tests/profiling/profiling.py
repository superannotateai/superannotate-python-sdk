import src.superannotate as sa

import time



stat = time.time()
sa.search_annotation_classes("Vector Project")
end = time.time()
print(11, end-stat)
