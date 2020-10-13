import pandas as pd


def filter_annotation_instances(annotations_df, include=None, exclude=None):
    """Filter annotation instances from project annotations pandas DataFrame.

    include and exclude rulses should be a list of rules of following type: [{"className": "<className>", "type" : "<bbox, polygon,...>", "attributes" : [{"name" : "<attribute_value>", "groupName" : "<attribute_group_name>"},...]},...]


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

            df = df.drop(df_new.index)

    result = annotations_df.loc[df.index]
    return result
