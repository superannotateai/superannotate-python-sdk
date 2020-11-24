import pandas as pd
from tqdm import tqdm
import plotly.express as px

def image_analytics(annotations_df, visualize = False):
    """
    Aggregates image analytics: num instances/annotation time in seconds per image
    :param annotations_df: pandas DataFrame of project annotations
    :type annotations_df: pandas.DataFrame
    :param visulaize: enables image analytics scatter plot
    :type visualize: bool

    :return: DataFrame on image analytics with columns ["userEmail", "userRole", "imageName", "annotationTime", "instanceCount"]
    :rtype: pandas DataFrame

    """
    def fix_spent_time(grp: pd.Series) -> pd.Series:
        grp = grp.copy()
        grp_lost_msk = (grp > 600) | (grp.isna())
        grp.loc[grp_lost_msk] = grp[~grp_lost_msk].median()
        return grp
    
    analytics = {"userEmail": [], "userRole": [], "imageName": [], "annotationTime": [], "instanceCount": [] }
    annot_cols = ["imageName", "instanceId", "createdAt", "creatorEmail", "creatorRole"]
    annotations_df = annotations_df[annotations_df["creationType"] == "Manual"][annot_cols].drop_duplicates()

    for annot, grp in annotations_df.groupby(["creatorEmail", "creatorRole"]):
        grp_sorted = grp.sort_values("createdAt")
        time_spent = grp_sorted.createdAt.diff().shift(-1).dt.total_seconds()
        grp["time_spent"] = fix_spent_time(time_spent)
        img_time = grp.groupby("imageName", as_index=False)["time_spent"].agg("sum")
        img_n_instance = grp.groupby("imageName")["instanceId"].agg("count")

        analytics["imageName"] += img_time.imageName.tolist()
        analytics["annotationTime"] += img_time.time_spent.tolist()
        analytics["instanceCount"] += img_n_instance.tolist()
        analytics["userEmail"] += [annot[0]] * len(img_time)
        analytics["userRole"] += [annot[1]] * len(img_time)

    analytics_df = pd.DataFrame(analytics)
    if visualize:
        #scatter plot of number of instances vs annotation time
        fig = px.scatter(
            analytics_df,
            x="instanceCount",
            y="annotationTime",
            color="userEmail",
            facet_col="userRole",
            custom_data = ["imageName"],
            labels = {'userEmail': "User Email", "instanceCount": "Number of Instances", "annotationTime": "Annotation time"},
            color_discrete_sequence=px.colors.qualitative.Dark24,
        )
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        fig.update_traces(hovertemplate="%{customdata[0]}")
        fig.show()
    return analytics_df
