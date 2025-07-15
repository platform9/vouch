#!/bin/bash


set -exu
CONTAINER_BUILD_IMAGE=artifactory.platform9.horse/docker-local/py39-build-image:pcd-graviton-v2

THIS_FILE=$(realpath $0)
THIS_DIR=$(dirname ${THIS_FILE})
BUILD_UID=$(id -u)
BUILD_GID=$(id -g)
docker run -i --rm -a stdout -a stderr \
   -v ${THIS_DIR}:/buildroot/vouch \
   -v ${THIS_DIR}/../vault:/buildroot/vault \
   -e PF9_VERSION=${PF9_VERSION} \
   -e BUILD_NUMBER=${BUILD_NUMBER} \
   -u ${BUILD_UID}:${BUILD_GID} \
   ${CONTAINER_BUILD_IMAGE} \
   /buildroot/vouch/stage-with-container-build.sh
