import os


def list_files_path(path_dir):
    list_files = []

    dir_list = os.walk(path_dir)
    for path, dirs, files in dir_list:
        for file in files:
            list_files.append(path + '/' + file)
    return list_files


def get_files_list(files_path):
    images_path = []

    for path in files_path:
        if path.endswith('tif'):
            images_path.append(path[:-3])

    return images_path
