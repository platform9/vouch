FROM ubuntu:22.04

RUN apt-get -y update
RUN apt-get -y install gettext-base
RUN apt-get -y install wget
RUN apt-get -y install vim
RUN apt-get -y install curl
RUN apt-get -y install net-tools
RUN apt-get -y install unzip
RUN apt-get -y install python3-dev
RUN apt-get -y install build-essential
RUN apt-get -y install python3-pip
RUN apt-get -y install libmysqlclient-dev
RUN apt-get -y install default-libmysqlclient-dev
RUN apt-get -y install libssl-dev
RUN apt-get -y install mysql-client
RUN apt-get -y install python3-openssl
RUN apt-get -y install pkg-config
RUN apt-get -y install jq

RUN cd /bin && curl -o kubectl https://s3.us-west-2.amazonaws.com/amazon-eks/1.34.2/2025-11-13/bin/linux/amd64/kubectl
RUN chmod +x /bin/kubectl

RUN pip install kubernetes
RUN pip install prometheus_client
RUN pip install sanic

# install vouch
#COPY vouch-sdist.tgz vault-sdist.tgz /tmp/
#RUN pip install --no-cache-dir /tmp/vouch-sdist.tgz \
# /tmp/vault-sdist.tgz \
# && rm -f /tmp/vouch-sdist.tgz /tmp/vault-sdist.tgz \
# && ln -s /usr/local/bin/init-region /root/init-region \
######### && ln -s /usr/local/bin/renew-token /root/renew-token

RUN mkdir -p /templates /vouch /root
COPY vouch/* /vouch/
COPY templates/* /templates/
COPY etc/ /etc
COPY scripts/ /

# init-region must be in this specific place
COPY scripts/init-region /root/init-region

ARG APP_METADATA
LABEL com.platform9.app_metadata=${APP_METADATA}
ARG VERSION
LABEL com.platform9.pf9_version=${VERSION}
ARG BUILD_ID
LABEL com.platform9.build=${BUILD_ID}
LABEL com.platform9.version="${VERSION}-${BUILD_ID}"
ARG BRANCH
LABEL com.platform9.branch=${BRANCH}

ENTRYPOINT ["/vouch.sh"]
