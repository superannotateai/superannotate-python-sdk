import os
import tempfile
from os.path import dirname
from pathlib import Path

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestFilterInstances(BaseTestCase):
    PROJECT_NAME = "test filter instances"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    PROJECT_DESCRIPTION = "desc"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_filter_comments(self):
        not_filtered = sa.aggregate_annotations_as_df(
            self.folder_path, include_comments=True
        )

        filtered_excl = sa.filter_images_by_comments(not_filtered, False, False, False)

        self.assertFalse(len(filtered_excl))

        filtered_excl = sa.filter_images_by_comments(
            not_filtered, include_unresolved_comments=True
        )

        self.assertEqual(
            sorted(filtered_excl), ["example_image_1.jpg", "example_image_2.jpg"]
        )

        filtered_excl = sa.filter_images_by_comments(not_filtered, False)

        self.assertFalse(len(filtered_excl))

        filtered_excl = sa.filter_images_by_comments(
            not_filtered,
            include_unresolved_comments=False,
            include_resolved_comments=True,
        )

        self.assertEqual(filtered_excl, ["example_image_1.jpg"])

        filtered_excl = sa.filter_images_by_comments(
            not_filtered,
            include_unresolved_comments=False,
            include_resolved_comments=True,
            include_without_comments=True,
        )

        self.assertEqual(
            sorted(filtered_excl),
            ["example_image_1.jpg", "example_image_3.jpg", "example_image_4.jpg"],
        )

        filtered_excl = sa.filter_images_by_comments(
            not_filtered,
            include_unresolved_comments=False,
            include_resolved_comments=False,
            include_without_comments=True,
        )

        self.assertEqual(
            sorted(filtered_excl), ["example_image_3.jpg", "example_image_4.jpg"]
        )

    def test_filter_tags(self):

        not_filtered = sa.aggregate_annotations_as_df(
            self.folder_path, include_tags=True
        )
        filtered_excl = sa.filter_images_by_tags(not_filtered)

        self.assertEqual(
            sorted(filtered_excl),
            ["example_image_2.jpg", "example_image_3.jpg", "example_image_4.jpg"],
        )

        filtered_excl = sa.filter_images_by_tags(not_filtered, include=["tag1"])

        self.assertEqual(
            sorted(filtered_excl), ["example_image_2.jpg", "example_image_4.jpg"]
        )

        filtered_excl = sa.filter_images_by_tags(not_filtered, exclude=["tag2"])

        self.assertEqual(sorted(filtered_excl), ["example_image_4.jpg"])

        filtered_excl = sa.filter_images_by_tags(
            not_filtered, include=["tag1", "tag2"], exclude=["tag3"]
        )

        self.assertEqual(
            sorted(filtered_excl), ["example_image_2.jpg", "example_image_4.jpg"]
        )

    def test_filter_instances(self):
        not_filtered = sa.aggregate_annotations_as_df(self.folder_path)
        filtered_excl = sa.filter_annotation_instances(
            not_filtered,
            exclude=[{"className": "Personal vehicle"}, {"className": "Human"}],
        )

        filtered_incl = sa.filter_annotation_instances(
            not_filtered,
            include=[{"className": "Large vehicle"}, {"className": "Plant"}],
        )

        self.assertTrue(filtered_incl.equals(filtered_excl))

        all_filtered = sa.filter_annotation_instances(
            not_filtered, include=[{"className": "bogus"}]
        )

        self.assertEqual(len(all_filtered), 0)

        vc = not_filtered["type"].value_counts()
        for i in vc.index:
            all_filtered = sa.filter_annotation_instances(
                not_filtered, include=[{"type": i}]
            )

            self.assertEqual(len(all_filtered), vc[i])

        vcc = not_filtered["className"].value_counts()
        for i in vcc.index:
            if len(not_filtered[not_filtered["className"] == i]["type"].unique()) > 1:
                break

        vcc_different_types = not_filtered[not_filtered["className"] == i][
            "type"
        ].value_counts()

        t_c = sa.filter_annotation_instances(
            not_filtered,
            include=[{"className": i, "type": vcc_different_types.index[0]}],
        )
        self.assertEqual(
            len(t_c),
            len(
                not_filtered[
                    (not_filtered["type"] == vcc_different_types.index[0])
                    & (not_filtered["className"] == i)
                ]
            ),
        )

    def test_df_to_annotations(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            df = sa.aggregate_annotations_as_df(self.folder_path)
            sa.df_to_annotations(df, tmp_dir)
            df_new = sa.aggregate_annotations_as_df(tmp_dir)

            assert len(df) == len(df_new)
            for _index, row in enumerate(df.iterrows()):
                for _, row_2 in enumerate(df_new.iterrows()):
                    if row_2[1].equals(row[1]):
                        break
                    # if row_2[1]["imageName"] == "example_image_1.jpg":
                    #     print(row_2[1])
                else:
                    assert False, print("Error on ", row[1])

            sa.upload_images_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
            sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
            )
            sa.upload_annotations_from_folder_to_project(
                self.PROJECT_NAME, self.folder_path
            )

    def test_df_to_annotations_full(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            df = sa.aggregate_annotations_as_df(
                self.folder_path,
                include_classes_wo_annotations=True,
                include_comments=True,
                include_tags=True,
            )
            sa.df_to_annotations(df, tmp_dir)
            df_new = sa.aggregate_annotations_as_df(
                tmp_dir,
                include_classes_wo_annotations=True,
                include_comments=True,
                include_tags=True,
            )
            sa.upload_images_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
            sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, Path(tmp_dir) / "classes" / "classes.json"
            )
            sa.upload_annotations_from_folder_to_project(self.PROJECT_NAME, tmp_dir)
            for _index, row in enumerate(df.iterrows()):
                for _, row_2 in enumerate(df_new.iterrows()):
                    if row_2[1].equals(row[1]):
                        break
                else:
                    assert False

            fil1 = sa.filter_annotation_instances(
                df_new,
                include=[
                    {
                        "className": "Personal vehicle",
                        "attributes": [{"name": "4", "groupName": "Num doors"}],
                    }
                ],
                exclude=[{"type": "polygon"}],
            )
            filtered_export = Path(tmp_dir) / "filtered"
            filtered_export.mkdir()
            sa.df_to_annotations(fil1, filtered_export)
            sa.upload_images_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
            sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, filtered_export / "classes" / "classes.json"
            )
            sa.upload_annotations_from_folder_to_project(
                self.PROJECT_NAME, filtered_export
            )
