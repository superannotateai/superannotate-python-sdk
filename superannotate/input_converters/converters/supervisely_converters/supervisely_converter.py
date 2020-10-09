class SuperviselyConverter(object):
    def __init__(self, args):

        self.dataset_name = args.dataset_name
        self.project_type = args.project_type
        self.task = args.task
        self.output_dir = args.output_dir
        self.export_root = args.export_root
        self.direction = args.direction

    def set_output_dir(self, output_dir_):
        self.output_dir = output_dir_

    def set_export_root(self, export_root_):
        self.export_root = export_root_

    def set_dataset_name(self, dname):
        self.dataset_name = dname