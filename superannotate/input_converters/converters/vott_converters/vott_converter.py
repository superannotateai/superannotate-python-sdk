from pathlib import Path
import logging

logger = logging.getLogger("superannotate-python-sdk")


class VoTTConverter():
    def __init__(self, args):
        logger.warning(
            "Beta feature. VoTT to SuperAnnotate annotation format converter is in BETA state."
        )
        self.dataset_name = args.dataset_name
        self.project_type = args.project_type
        self.task = args.task
        self.output_dir = args.output_dir
        self.export_root = args.export_root
        self.direction = args.direction
        self.platform = args.platform

    def get_file_list(self):
        json_file_list = []
        path = Path(self.export_root)
        if self.dataset_name != '':
            json_file_list.append(path.joinpath(self.dataset_name + '.json'))
        else:
            file_generator = path.glob('*.json')
            for gen in file_generator:
                json_file_list.append(gen)

        return json_file_list
