#!/bin/bash

# docker build -t superannotate/pythonsdk-dev-env:latest -f Dockerfile_dev_env .
# docker pull superannotate/pythonsdk-dev-env:latest

# docker run -it -p 8888:8888 \
#     -v ${HOME}/.superannotate:/root/.superannotate \
#     -v $(pwd):/root/superannotate-python-sdk \
#     superannotate/pythonsdk-dev-env \
#     bash -c "pip install -e superannotate-python-sdk && jupyter lab --allow-root --NotebookApp.token='' --NotebookApp.password='' --no-browser --ip 0.0.0.0"

docker run -it -p 8888:8888 \
    -v ${HOME}/.superannotate:/root/.superannotate \
    -v $(pwd):/root/superannotate-python-sdk \
    superannotate/pythonsdk-dev-env
