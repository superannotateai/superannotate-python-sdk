class VocConverter():
    def __init__(self, args):

        self.project_type = args.project_type
        self.dataset_name = args.dataset_name
        self.export_root = args.export_root
        self.output_dir = args.output_dir
        self.task = args.task
        self.direction = args.direction
        self.platform = args.platform
