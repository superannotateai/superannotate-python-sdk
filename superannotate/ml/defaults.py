DEFAULT_HYPERPARAMETERS = {
    "instance_type":"1xK80-12GB",
    "num_epochs": 12,
    "dataset_split_ratio": 80,
    "base_lr": 0.02,
    "gamma": 0.5,
    "images_per_batch": 4,
    "batch_per_image": 512,
    "steps": [5],
    "evaluation_period": 12,
    "runtime_seconds" : 600,
    "estimated_remaining_time": 600,
    "template_id": None
}

NON_PLOTABLE_KEYS = ['eta_seconds', 'iteration' ,'data_time','time','model']
DROP_KEYS = ['eta_seconds', 'data_time', 'time']


