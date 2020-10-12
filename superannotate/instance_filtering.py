import pandas as pd


def filter_annotation_instances(annotations_df, include=None, exclude=None):
    df = annotations_df.drop(["meta", "point_labels"], axis=1)

    if include is not None:
        included_dfs = []
        for include_rule in include:
            df_new = df.copy()
            if "className" in include_rule:
                df_new = df_new[df_new["class"] == include_rule["className"]]
            if "attributes" in include_rule:
                for attribute in include_rule["attributes"]:
                    df_new = df_new[
                        df_new["attribute_group"] == attribute["groupName"] &
                        df_new["attribute_name"] == attribute["name"]]
            if "type" in include_rule:
                df_new = df_new[df_new["type"] == include_rule["type"]]
            included_dfs.append(df_new)

        df = pd.concat(included_dfs)

    if exclude is not None:
        excluded_dfs = []
        for exclude_rule in exclude:
            df_new = df.copy()
            if "className" in exclude_rule:
                df_new = df_new[df_new["class"] == exclude_rule["className"]]
            if "attributes" in exclude_rule:
                for attribute in exclude_rule["attributes"]:
                    df_new = df_new[
                        df_new["attribute_group"] == attribute["groupName"] &
                        df_new["attribute_name"] == attribute["name"]]
            if "type" in exclude_rule:
                df_new = df_new[df_new["type"] == exclude_rule["type"]]
            excluded_dfs.append(df_new)

        to_exclude = pd.concat(excluded_dfs)
        df = df.merge(to_exclude, how='outer',
                      indicator=True).loc[lambda x: x['_merge'] == 'left_only']
        df = df.drop("_merge", axis=1)

    return annotations_df.loc[df.index]
