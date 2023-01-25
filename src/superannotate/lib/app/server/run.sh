#!/bin/bash

########################################################

## Shell Script to Build and Run Docker Image

########################################################


echo "build the docker image"
sudo docker build . -t sa_server
echo "built docker images and proceeding to delete existing container"
result=$(docker ps -q -f name=sa_server)
if [[ $? -eq 0 ]]; then
  echo "Container exists"
  sudo docker container rm -f sa_server
  echo "Deleted the existing docker container"
else
  echo "No such container"
fi
echo "Deploying the updated container"
#sudo docker run -d sa_server -p 80:80
sudo docker run sa_server
echo "Deploying the container"
