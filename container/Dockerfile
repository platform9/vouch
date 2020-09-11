from python:2.7-alpine

# libffi-dev and build-base required by python's cryptography
# mariadb-connector-c-dev/mysql_config required for python's mysqlclient
RUN apk add libffi-dev mariadb-connector-c-dev build-base

# install confd
RUN wget -O /usr/bin/confd \
    https://github.com/kelseyhightower/confd/releases/download/v0.15.0/confd-0.15.0-linux-amd64 \
    && chmod 755 /usr/bin/confd

# install vouch and supervisor
COPY vouch-sdist.tgz firkinize-sdist.tgz vault-sdist.tgz /tmp/
RUN pip install --no-cache-dir /tmp/vouch-sdist.tgz /tmp/firkinize-sdist.tgz \
 /tmp/vault-sdist.tgz supervisor \
 && rm -f /tmp/vouch-sdist.tgz /tmp/firkinize-sdist.tgz /tmp/vault-sdist.tgz \
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
