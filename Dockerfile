FROM ubuntu:20.04
ENV LANG C.UTF-8

ARG PIP_FLAGS

SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND noninteractive
ENV HOME /root
WORKDIR $HOME

RUN apt-get update && apt-get install -y --no-install-recommends \
  ca-certificates python3 python3-pip python3-venv ffmpeg libgl1-mesa-dev libglib2.0-0 libsm6 libxrender1 libxext6 nano vim htop && \
  rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1
RUN update-alternatives --install /usr/local/bin/pip pip /usr/bin/pip3 1

ENV VIRTUAL_ENV=$HOME/venv_superannotatesdk
RUN python -m venv ${VIRTUAL_ENV}
ENV PATH="${VIRTUAL_ENV}/bin:$PATH"

RUN pip install --no-cache-dir ${PIP_FLAGS} superannotate && \
  pip install --no-cache-dir jupyterlab && \
  pip install --no-cache-dir xeus-python notebook && \
  rm -rf /root/.cache/pip

CMD ["jupyter", "lab", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''", "--no-browser", "--ip", "0.0.0.0"]