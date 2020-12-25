'''
'''
from .dataloop_to_sa_vector import dataloop_to_sa
from ..baseStrategy import baseStrategy

from ....common import dump_output


class DataLoopStrategy(baseStrategy):
    name = "DataLoop converter"

    def __init__(self, args):
        super().__init__(args)
        self.conversion_algorithm = dataloop_to_sa

    def __str__(self):
        return '{} object'.format(self.name)

    def to_sa_format(self):
        sa_jsons, sa_classes = self.conversion_algorithm(
            self.export_root, self.task
        )
        dump_output(self.output_dir, self.platform, sa_classes, sa_jsons)
