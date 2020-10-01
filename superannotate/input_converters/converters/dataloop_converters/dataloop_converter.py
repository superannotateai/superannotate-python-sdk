class DataLoopConverter(object):
    def __init__(
        self, dataset_name_, exprot_root_, project_type_, output_dir_, task_
    ):
        self.dataset_name = dataset_name_
        self.project_type = project_type_
        self.task = task_
        self.output_dir = output_dir_
        self.export_root = exprot_root_

    def set_output_dir(self, output_dir_):
        self.output_dir = output_dir_

    def set_export_root(self, exprot_root_):
        self.exprot_root = exprot_root_

    def set_dataset_name(self, dname):
        self.dataset_name = dname
