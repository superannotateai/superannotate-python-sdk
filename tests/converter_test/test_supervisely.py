import superannotate as sa


def supervisely_convert(tmpdir):
    out_dir = tmpdir / 'output'
    sa.import_annotation_format(
        'tests/converter_test/Supervisely/input/toSuperAnnotate', str(out_dir),
        'Supervisely', '', 'Vector', 'vector_annotation', 'Web'
    )
    return 0


def test_supervisely(tmpdir):
    assert supervisely_convert(tmpdir) == 0
