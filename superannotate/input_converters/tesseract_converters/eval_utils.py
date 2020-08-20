import os


def get_accuracy(ground_truth, output_file, method='char'):
    if os.path.exists(ground_truth) and os.path.exists(output_file):
        if method == "word":
            os.system("wordacc %s %s report.txt" % (ground_truth, output_file))
        elif method == "char":
            os.system("accuracy %s %s report.txt" %
                      (ground_truth, output_file))
        else:
            raise ValueError("method must be 'word' or 'char'")

        file = open("report.txt", "r")
        for i in range(4):
            file.readline()

        accuracy = float(file.readline().split("%")[0])
        os.remove("report.txt")
        return accuracy
    else:
        print("ERROR: '%s' or '%s' doesn't exist!" %
              (ground_truth, output_file))