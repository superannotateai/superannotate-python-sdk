class VocConverter(object):
    def __init__(self, args):

        self.project_type = args.project_type
        self.dataset_name = args.dataset_name
        self.export_root = args.export_root
        self.output_dir = args.output_dir
        self.task = args.task
        self.direction = args.direction

    def set_output_dir(self, output_dir):
        self.output_dir = output_dir

    def set_export_root(self, export_dir):
        self.export_root = export_dir

    def set_dataset_name(self, dname):
        self.dataset_name = dname