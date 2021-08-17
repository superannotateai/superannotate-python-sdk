import tempfile
from unittest import TestCase

import pydicom.data
import src.lib.app.superannotate as sa


class TestDicom(TestCase):
    def test_dicom_conversion(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = pydicom.data.get_testdata_file("CT_small.dcm")
            paths = sa.dicom_to_rgb_sequence(path, tmp_dir)
            self.assertEqual(len(paths), 1)
