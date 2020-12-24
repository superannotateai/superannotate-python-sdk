import numpy as np


def _create_classes(classes_map):
    classes_loader = []
    for key, value in classes_map.items():
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)
        sa_classes = {'name': value, 'color': hexcolor, 'attribute_groups': []}
        classes_loader.append(sa_classes)
    return classes_loader
