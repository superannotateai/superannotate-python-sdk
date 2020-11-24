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

    :return: DataFrame on image analytics with columns ["image", "instances", "time"]
    :rtype: pandas DataFrame

    """
    def fix_spent_time(grp: pd.Series) -> pd.Series:
        grp = grp.copy()
        grp_lost_msk = (grp > 600) | (grp.isna())
        grp.loc[grp_lost_msk] = grp[~grp_lost_msk].median()
        return grp
    
    analytics = {"user_id": [], "user_role": [], "image": [], "time": [], "ninstances": [] }
    annot_cols = ["imageName", "instanceId", "createdAt", "creatorEmail", "creatorRole"]
    annotations_df = annotations_df[annotations_df["creationType"] == "Manual"][annot_cols].drop_duplicates()

    for annot, grp in annotations_df.groupby(["creatorEmail", "creatorRole"]):
        grp_sorted = grp.sort_values("createdAt")
        time_spent = grp_sorted.createdAt.diff().shift(-1).dt.total_seconds()
        grp["time_spent"] = fix_spent_time(time_spent)
        img_time = grp.groupby("imageName", as_index=False)["time_spent"].agg("sum")
        img_n_instance = grp.groupby("imageName")["instanceId"].agg("count")

        analytics["image"] += img_time.imageName.tolist()
        analytics["time"] += img_time.time_spent.tolist()
        analytics["ninstances"] += img_n_instance.tolist()
        analytics["user_id"] += [annot[0]] * len(img_time)
        analytics["user_role"] += [annot[1]] * len(img_time)

    analytics_df = pd.DataFrame(analytics)
    if visualize:
        #scatter plot of number of instances vs annotation time
        fig = px.scatter(
            analytics_df,
            x="ninstances",
            y="time",
            color="user_id",
            facet_col="user_role",
            custom_data = ["image"],
            color_discrete_sequence=px.colors.qualitative.Dark24,
            labels = {'user_id': "User Email", "ninstances": "Number of Instances", "time": "Annotation time"}
        )
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        fig.update_traces(hovertemplate="%{customdata[0]}")
        fig.show()
    return analytics_df
