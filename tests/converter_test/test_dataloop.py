import superannotate as sa


def dataloop_convert(tmpdir):
    out_dir = tmpdir / 'output'
    sa.import_annotation_format(
        'tests/converter_test/DataLoop/input/toSuperAnnotate', out_dir,
        'DataLoop', '', 'Vector', 'vector_annotation', 'Web'
    )
    return 0


def test_dataloop(tmpdir):
    assert dataloop_convert(tmpdir) == 0
