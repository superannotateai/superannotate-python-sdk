from ast import literal_eval
import pandas as pd
from .defaults import DROP_KEYS
def reformat_metrics_json(data, name):
    continuous_metrics = []
    per_evaluation_metrics = []
    for item in data:
        for key in item:
            try:
                item[key] = literal_eval(item[key])
            except Exception as e:
                pass
        if 'data_time' in item and item['eta_seconds'] != 0:
            continuous_metrics += [item]
        else:
            per_evaluation_metrics += [item]
    continuous_metrics_df = pd.DataFrame.from_dict(continuous_metrics)
    per_evaluation_metrics_df = pd.DataFrame.from_dict(per_evaluation_metrics)
    continuous_metrics_df = drop_non_plotable_cols(continuous_metrics_df, DROP_KEYS)
    per_evaluation_metrics_df = drop_non_plotable_cols(per_evaluation_metrics_df, DROP_KEYS)
    continuous_metrics_df['model'] = name
    per_evaluation_metrics_df['model'] = name
    return continuous_metrics_df, per_evaluation_metrics_df

def drop_non_plotable_cols(df, non_plotable_cols):
    for column in df:
        if column not in non_plotable_cols:
            continue
        df = df.drop(columns = column)
    return df

def make_plotly_specs(num_rows):
    specs = [[{"secondary_y": True}] for x in range(num_rows)]
    return specs
