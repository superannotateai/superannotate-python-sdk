from pathlib import Path

import numpy as np
import pydicom
from PIL import Image


def dicom_to_rgb_sequence(
    input_dicom_file, output_dir, output_image_quality=100
):
    """Converts DICOM file to RGB image sequence.
    Output file format is <input_dicom_file_name_woextension>_<frame_number>.jpg

    :param input_dicom_file: path to DICOM file
    :type input_dicom_file: str or Pathlike
    :param output_dir: path to output directory
    :type output_dir: str or Pathlike
    :param output_image_quality: output JPEG quality setting in percents
    :type output_image_quality: int

    :return: paths to output images
    :rtype: list of strs

    """
    input_dicom_file = Path(input_dicom_file)
    ds = pydicom.dcmread(str(input_dicom_file))
    # interp = ds.PhotometricInterpretation
    # print(interp)

    arr = ds.pixel_array
    if "NumberOfFrames" in ds:
        number_of_frames = ds.NumberOfFrames
    else:
        number_of_frames = 1
        arr = arr[np.newaxis, :]
    # print(arr.shape)
    output_dir = Path(output_dir)
    output_paths = []
    for i in range(number_of_frames):
        image = Image.fromarray(arr[i])
        image = image.convert("RGB")
        path = output_dir / (input_dicom_file.stem + f"_{i:05}.jpg")
        image.save(
            path,
            subsampling=0 if output_image_quality > 80 else 2,
            quality=output_image_quality
        )
        output_paths.append(str(path))

    return output_paths
