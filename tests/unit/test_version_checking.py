from unittest import TestCase
from unittest.mock import patch
from unittest.mock import Mock
from tests.utils.helpers import catch_prints

import pytest

TEST_VERSION = "1.0.0b1"
TEST_NEW_MAJOR_VERSION = "22.2.2"
TEST_NEW_VERSION = "1.2.2"


mock_response_1 = Mock(status_code=200)
mock_response_1.json.return_value = {"releases": [TEST_NEW_MAJOR_VERSION]}
mock_get_1 = Mock(return_value=mock_response_1)

mock_response_2 = Mock(status_code=200)
mock_response_2.json.return_value = {"releases": [TEST_NEW_VERSION]}
mock_get_2 = Mock(return_value=mock_response_2)


class TestVersionCheck(TestCase):

    @pytest.mark.skip(reason="Need to adjust")
    @patch('superannotate.version.__version__', TEST_VERSION)
    @patch("requests.get", mock_get_1)
    def test_dev_version_first_info_log(self):
        with catch_prints() as out:
            import src.superannotate
            import src.superannotate.lib.core as constances
            logs = out.getvalue().split("\n")
            self.assertEqual(
                logs[0],
                "SA-PYTHON-SDK - INFO - " + constances.PACKAGE_VERSION_INFO_MESSAGE.format(TEST_VERSION)
            )

    @pytest.mark.skip(reason="Need to adjust")
    @patch('superannotate.version.__version__', TEST_VERSION)
    @patch("requests.get", mock_get_1)
    def test_dev_version_major_update(self):
        with catch_prints() as out:
            import src.superannotate
            import src.superannotate.lib.core as constances
            logs = out.getvalue().split("\n")
            self.assertEqual(
                logs[1],
                "SA-PYTHON-SDK - WARNING - " + constances.PACKAGE_VERSION_MAJOR_UPGRADE.format(
                    TEST_VERSION, TEST_NEW_MAJOR_VERSION
                )
            )

    @pytest.mark.skip(reason="Need to adjust")
    @patch('superannotate.version.__version__', TEST_VERSION)
    @patch("requests.get", mock_get_2)
    def test_dev_version_update(self):
        with catch_prints() as out:
            import src.superannotate
            import src.superannotate.lib.core as constances
            logs = out.getvalue().split("\n")
            self.assertEqual(
                logs[1],
                "SA-PYTHON-SDK - WARNING - " + constances.PACKAGE_VERSION_UPGRADE.format(TEST_VERSION,
                                                                                         TEST_NEW_VERSION)
            )

