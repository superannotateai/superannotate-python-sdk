import logging

logger = logging.getLogger("superannotate-python-sdk")


class YOLOConverter():
    def __init__(self, args):
        logger.warning(
            "Beta feature. YOLO to SuperAnnotate annotation format converter is in BETA state."
        )
        self.dataset_name = args.dataset_name
        self.project_type = args.project_type
        self.task = args.task
        self.output_dir = args.output_dir
        self.export_root = args.export_root
        self.direction = args.direction
        self.platform = args.platform
