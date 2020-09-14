class VocConverter(object):
    def __init__(
        self, dataset_name_, export_root_, project_type_, output_dir_, task_
    ):
        self.project_type = project_type_
        self.dataset_name = dataset_name_
        self.export_root = export_root_
        self.output_dir = output_dir_
        self.task = task_

    def set_output_dir(self, output_dir):
        self.output_dir = output_dir

    def set_export_root(self, export_dir):
        self.export_root = export_dir

    def set_dataset_name(self, dname):
        self.dataset_name = dname