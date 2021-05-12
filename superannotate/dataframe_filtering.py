import pandas as pd
from .mixp.decorators import Trackable


@Trackable
def filter_images_by_comments(
    annotations_df,
    include_unresolved_comments=True,
    include_resolved_comments=False,
    include_without_comments=False
):
    """Filter images on comment resolve status and comment existence

    :param annotations_df: pandas DataFrame of project annotations
    :type annotations_df: pandas.DataFrame
    :param include_unresolved_comments: include images with unresolved state
    :type include_unresolved_comments: bool
    :param include_resolved_comments: include images with resolved state
    :type include_resolved_comments: bool
    :param include_without_comments: include images without any comments
    :type include_without_comments: bool

    :return: filtered image names
    :rtype: list of strs

    """
    images = set()
    df = annotations_df[annotations_df["type"] == "comment"]
    if include_unresolved_comments:
        images.update(
            df[df["commentResolved"] == False]["imageName"].dropna().unique()
        )
    if include_resolved_comments:
        images.update(
            df[df["commentResolved"] == True]["imageName"].dropna().unique()
        )
    if include_without_comments:
        all_images = set(annotations_df["imageName"].dropna().unique())
        with_comments = set(df["imageName"].dropna().unique())
        images.update(all_images - with_comments)

    return list(images)


@Trackable
def filter_images_by_tags(annotations_df, include=None, exclude=None):
    """Filter images on tags

    :param annotations_df: pandas DataFrame of project annotations
    :type annotations_df: pandas.DataFrame
    :param include: include images with given tags
    :type include: list of strs
    :param exclude: exclude images with given tags
    :type exclude: list of strs

    :return: filtered image names
    :rtype: list of strs

    """

    df = annotations_df[annotations_df["type"] == "tag"]
    images = set(df["imageName"].dropna().unique())

    if include:
        include_images = set(
            df[df["tag"].isin(include)]["imageName"].dropna().unique()
        )
        images = images.intersection(include_images)

    if exclude:
        exclude_images = set(
            df[df["tag"].isin(exclude)]["imageName"].dropna().unique()
        )

        images = images.difference(exclude_images)

    return list(images)


@Trackable
def filter_annotation_instances(annotations_df, include=None, exclude=None):
    """Filter annotation instances from project annotations pandas DataFrame.

    include and exclude rules should be a list of rules of the following type:
    [{"className": "<className>", "type" : "<bbox, polygon,...>",
    "error": <True or False>, "attributes" : [{"name" : "<attribute_value>",
    "groupName" : "<attribute_group_name>"},...]},...]


    :param annotations_df: pandas DataFrame of project annotations
    :type annotations_df: pandas.DataFrame
    :param include: include rules
    :type include: list of dicts
    :param exclude: exclude rules
    :type exclude: list of dicts

    :return: filtered DataFrame
    :rtype: pandas.DataFrame

    """
    df = annotations_df.drop(["meta", "pointLabels"], axis=1)

    if include is not None:
        included_dfs = []
        for include_rule in include:
            df_new = df.copy()
            if "className" in include_rule:
                df_new = df_new[df_new["className"] == include_rule["className"]
                               ]
            if "attributes" in include_rule:
                for attribute in include_rule["attributes"]:
                    df_new = df_new[(
                        df_new["attributeGroupName"] == attribute["groupName"]
                    ) & (df_new["attributeName"] == attribute["name"])]
            if "type" in include_rule:
                df_new = df_new[df_new["type"] == include_rule["type"]]
            if "error" in include_rule:
                df_new = df_new[df_new["error"] == include_rule["error"]]
            included_dfs.append(df_new)

        df = pd.concat(included_dfs)

    if exclude is not None:
        for exclude_rule in exclude:
            df_new = df.copy()
            # with pd.option_context('display.max_rows', None):
            #     print("#", df_new["className"])
            if "className" in exclude_rule:
                df_new = df_new[df_new["className"] == exclude_rule["className"]
                               ]
            if "attributes" in exclude_rule:
                for attribute in exclude_rule["attributes"]:
                    df_new = df_new[
                        (df_new["attributeGroup"] == attribute["groupName"]) &
                        (df_new["attributeName"] == attribute["name"])]
            if "type" in exclude_rule:
                df_new = df_new[df_new["type"] == exclude_rule["type"]]
            if "error" in exclude_rule:
                df_new = df_new[df_new["error"] == exclude_rule["error"]]

            df = df.drop(df_new.index)

    result = annotations_df.loc[df.index]
    return result
