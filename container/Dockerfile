from artifactory.platform9.horse/docker-local/pf9-py39-baseimg-alpine:stable

RUN apk update && apk add bash \
    && apk add curl \
    && rm -vrf /var/cache/apk/*

# install vouch
COPY vouch-sdist.tgz vault-sdist.tgz /tmp/
RUN pip install --no-cache-dir /tmp/vouch-sdist.tgz \
 /tmp/vault-sdist.tgz \
 && rm -f /tmp/vouch-sdist.tgz /tmp/vault-sdist.tgz \
 && ln -s /usr/local/bin/init-region /root/init-region

COPY etc/ /etc

ARG APP_METADATA
LABEL com.platform9.app_metadata=${APP_METADATA}
ARG VERSION
LABEL com.platform9.pf9_version=${VERSION}
ARG BUILD_ID
LABEL com.platform9.build=${BUILD_ID}
LABEL com.platform9.version="${VERSION}-${BUILD_ID}"
ARG BRANCH
LABEL com.platform9.branch=${BRANCH}
