import pytest
from pathlib import Path
import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

test_root = Path().resolve().parent


@pytest.mark.parametrize(
    "export_root, project_names, total_instances, instances_per_class", [
        (
            test_root, ["sample_project_vector"], 73, {
                "Human": 10,
                "Personal vehicle": 56,
                "Large vehicle": 7,
                "Plant": 0
            }
        ),
        (
            test_root, ["sample_project_pixel"], 85, {
                "Pedestrian": 3,
                "Traffic sign": 13,
                "Personal vehicle": 65,
                "Large vehicle": 3,
                "Two wheeled vehicle": 1
            }
        ),
        (
            test_root, ["sample_project_vector", "sample_project_pixel"], 158, {
                "Personal vehicle": 121,
                "Large vehicle": 10,
                "Human": 10,
                "Pedestrian": 3,
                "Traffic sign": 13,
                "Two wheeled vehicle": 1,
                "Plant": 0
            }
        )
    ]
)
def test_class_distribution(
    export_root, project_names, total_instances, instances_per_class
):

    df = sa.class_distribution(export_root, project_names)
    assert df["count"].sum() == total_instances

    for class_name, gt_instance_count in instances_per_class.items():
        df_instance_count = df.loc[df['className'] == class_name,
                                   'count'].item()
        assert df_instance_count == gt_instance_count


@pytest.mark.parametrize(
    "export_root, project_names, total_attributes, attributes_per_class", [
        (
            test_root, ["sample_project_vector"], 3, {
                "Personal vehicle": {
                    "Num doors": {
                        "2": 1,
                        "4": 0
                    }
                },
                "Large vehicle":
                    {
                        "Num doors": {
                            "2": 0,
                            "4": 1
                        },
                        "swedish": {
                            "yes": 0,
                            "no": 1
                        }
                    },
                "Human": {
                    "Height": {
                        "Tall": 0,
                        "Short": 0
                    }
                },
            }
        ),
        (
            test_root, ["sample_project_pixel"], 2, {
                "Personal vehicle": {
                    "Large": {
                        "no": 0,
                        "yes": 1
                    }
                },
                "Large vehicle": {
                    "small": {
                        "no": 1,
                        "yes": 0
                    }
                },
            }
        ),
        (
            test_root, ["sample_project_vector", "sample_project_pixel"], 5, {
                "Personal vehicle":
                    {
                        "Num doors": {
                            "2": 1,
                            "4": 0
                        },
                        "Large": {
                            "no": 0,
                            "yes": 1
                        }
                    },
                "Large vehicle":
                    {
                        "Num doors": {
                            "2": 0,
                            "4": 1
                        },
                        "swedish": {
                            "yes": 0,
                            "no": 1
                        },
                        "small": {
                            "no": 1,
                            "yes": 0
                        }
                    },
                "Human": {
                    "Height": {
                        "Tall": 0,
                        "Short": 0
                    }
                },
            }
        )
    ]
)
def test_attribute_distribution(
    export_root, project_names, total_attributes, attributes_per_class
):

    df = sa.attribute_distribution(export_root, project_names)
    assert df["count"].sum() == total_attributes

    for class_name, class_attribute_groups in attributes_per_class.items():
        for attribute_group_name, attribute_group in class_attribute_groups.items(
        ):
            for attribute_name, count in attribute_group.items():
                assert df.loc[
                    (df['className'] == class_name) &
                    (df['attributeGroupName'] == attribute_group_name) &
                    (df['attributeName'] == attribute_name),
                    'count'].item() == count
