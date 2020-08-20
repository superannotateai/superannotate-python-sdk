import os
import json
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input',
        help='Path to input files or folder\
                        with tesseract dict format.\
                        File name structure \
                        [IMAGE_NAME]___tess.json',
        required=True
    )
    parser.add_argument(
        '--output',
        help='Path to output folder.\
                        File name structure \
                        [IMAGE_NAME]___objects.json'
    )
    parser.add_argument(
        '--verbose',
        default='0',
        choices=['0', '1', '2'],
        help="0 -- Doesn't print anything,\
        1 -- Prints number of converted files,\
        2 -- Prints number of converted files and unconverted files path."
    )
    args = parser.parse_args()

    input_files_list = get_input_list(args.input)
    file_name = [os.path.basename(file) for file in input_files_list]

    output_files_list = []
    if args.output == None:
        output_files_list = get_output_list(file_name)
    else:
        output_files_list = get_output_list(file_name, args.output)

    converter(input_files_list, output_files_list, args.verbose)


def get_input_list(pathname):
    input_files_list = []
    try:
        if os.path.isfile(pathname):
            input_files_list.append(os.path.abspath(pathname))
        else:
            list_files = os.listdir(pathname)
            abs_path = os.path.abspath(pathname)
            for file in list_files:
                input_files_list.append(os.path.join(abs_path, file))
    except IOError:
        print("ERROR: '%s' file or folder doesn't exist!" % (pathname))
    return input_files_list


def get_output_list(input_list, pathname='./output'):
    if os.path.exists(pathname):
        abs_path = os.path.abspath(pathname)
    else:
        os.makedirs(pathname)
        abs_path = os.path.abspath(pathname)

    output_files_list = []
    for file in input_list:
        output_files_list.append(
            os.path.join(abs_path,
                         file.split("___")[0] + "___objects.json")
        )

    return output_files_list


def converter(input_files_list, output_files_list, verbose=0):
    converted = 0
    for file_in, file_out in zip(input_files_list, output_files_list):
        try:
            file_json = json.load(open(file_in))
            output = []
            for i in range(len(file_json['level'])):
                if file_json["text"][i] != "" and file_json["text"][i] != " ":
                    dd = {
                        "type": "bbox",
                        "points":
                            {
                                "x1":
                                    file_json["left"][i],
                                "y1":
                                    file_json["top"][i],
                                "x2":
                                    file_json["left"][i] +
                                    file_json["width"][i],
                                "y2":
                                    file_json["top"][i] + file_json["height"][i]
                            },
                        "className": "Text",
                        "classId": 2031,
                        "pointLabels": {
                            "0": file_json["text"][i]
                        },
                        "attributes": [],
                        "probability": 100,
                        "locked": False,
                        "visible": True,
                        "groupId": 0,
                        "imageId": 0
                    }
                    output.append(dd)
            json.dump(output, open(file_out, "w"), indent=2)
            converted += 1
        except ValueError:
            if verbose == '2':
                print("WARNING: '%s' file is not json format!" % (file_in))

    if int(verbose) > 0:
        print(
            "Converted to sa format: %d of %d" %
            (converted, len(input_files_list))
        )


if __name__ == '__main__':
    main()