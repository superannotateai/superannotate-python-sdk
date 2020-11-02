import superannotate as sa

print('one')
sa.import_annotation_format(
    'SageMaker/input/toSuperAnnotate/object_detection', 'output', 'SageMaker',
    'test-obj-detect', 'Vector', 'object_detection', 'Web'
)

print('two')
sa.import_annotation_format(
    'SageMaker/input/toSuperAnnotate/instance_segmentation', 'output2',
    'SageMaker', 'test-obj-detect', 'Pixel', 'instance_segmentation', 'Web'
)