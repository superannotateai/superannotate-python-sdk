import pydicom.data

import superannotate as sa


def test_dicom_convesion(tmpdir):
    print("Using temp dir", tmpdir)
    path = pydicom.data.get_testdata_file("CT_small.dcm")
    print("Using dicom file", path)
    paths = sa.dicom_to_rgb_sequence(path, tmpdir)
    assert len(paths) == 1
