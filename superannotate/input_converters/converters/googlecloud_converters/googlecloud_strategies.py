from pathlib import Path

from .googlecloud_to_sa_vector import googlecloud_to_sa_vector

from ..baseStrategy import baseStrategy

from ....common import dump_output


class GoogleCloudStrategy(baseStrategy):
    name = "GoogleCloud converter"

    def __init__(self, args):
        super().__init__(args)
        self.conversion_algorithm = googlecloud_to_sa_vector

    def __str__(self):
        return '{} object'.format(self.name)

    def to_sa_format(self):
        path = Path(self.export_root).joinpath(self.dataset_name + '.csv')
        sa_jsons, sa_classes = self.conversion_algorithm(path)
        dump_output(self.output_dir, self.platform, sa_classes, sa_jsons)
