FROM ubuntu:20.04
ENV LANG C.UTF-8

ARG PIP_FLAGS

SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND noninteractive
ENV PATH="/root/.local/bin:${PATH}"


RUN apt-get update && apt-get install -y \
	ca-certificates python3 python3-pip libgl1-mesa-dev libglib2.0-0 libsm6 libxrender1 libxext6 nano vim htop && \
  rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1
RUN update-alternatives --install /usr/local/bin/pip pip /usr/bin/pip3 1

RUN apt-get install -y build-essential && \
    pip install --no-cache-dir ${PIP_FLAGS} srannotate && \
    apt-get remove -y build-essential && \
    apt-get -y autoremove && \
    rm -rf /root/.cache/pip && \
    rm -rf /var/lib/apt/lists/*

CMD ["/bin/bash"]
