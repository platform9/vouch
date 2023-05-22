
.SUFFIXES:
.PHONY: clean push image stage dist unit-test stage-with-py-container

SRCROOT = $(abspath $(dir $(CURDIR)/$(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))))
BUILD_DIR := $(SRCROOT)/build
VENV := $(SRCROOT)/.venv
STAGE = $(BUILD_DIR)/container
$(shell mkdir -p $(STAGE))

VOUCH_CODE = $(shell find $(SRCROOT)/vouch -name '*.py') $(SRCROOT)/setup.py
VOUCH_DIST = $(STAGE)/vouch-sdist.tgz

VAULTROOT = $(abspath $(SRCROOT)/../vault)
VAULT_CODE = $(shell find $(VAULTROOT) -name '*.py') $(VAULTROOT)/setup.py
VAULT_DIST = $(STAGE)/vault-sdist.tgz

export BUILD_NUMBER ?= 0
export PF9_VERSION ?= 0.0.0
DOCKER_REPOSITORY ?= quay.io/platform9/vouch
BUILD_ID := $(BUILD_NUMBER)
IMAGE_TAG ?= "$(or $(PF9_VERSION), $(PF9_VERSION), "latest")-$(BUILD_ID)"
BRANCH_NAME ?= $(or $(TEAMCITY_BUILD_BRANCH), $(TEAMCITY_BUILD_BRANCH), $(shell git symbolic-ref --short HEAD))

dist: $(VOUCH_DIST) $(VAULT_DIST)

$(VOUCH_DIST): $(VOUCH_CODE)
	id && echo $(PATH) && \
	cd $(SRCROOT) && \
	rm -f dist/vouch* && \
	python3 setup.py sdist && \
	cp dist/vouch* $@

$(VAULT_DIST): $(VAULT_CODE)
	cd $(VAULTROOT) && \
	rm -f dist/vault* && \
	python3 setup.py sdist && \
	cp dist/vault* $@

stage-with-py-container: dist

stage:
	$(SRCROOT)/run-staging-in-container.sh && \
	cp -r $(SRCROOT)/container/* $(STAGE)/

$(BUILD_DIR):
	mkdir -p $@

$(VENV):
	(test -d $(VENV) || virtualenv $(VENV)) && \
	$(VENV)/bin/python $(VENV)/bin/pip install pip==19.0.3 setuptools==42.0.2

$(BUILD_DIR)/container-tag: $(BUILD_DIR)
	echo -ne "$(IMAGE_TAG)" >$@

unit-test: $(VENV)
	$(VENV)/bin/python $(VENV)/bin/pip install -e$(SRCROOT) \
	-e$(VAULTROOT) nose && \
	$(VENV)/bin/nosetests -vd .

image: stage
	docker build -t $(DOCKER_REPOSITORY):$(IMAGE_TAG) \
		--build-arg BUILD_ID=$(BUILD_ID) \
		--build-arg VERSION=$(PF9_VERSION) \
		--build-arg BRANCH=$(BRANCH_NAME) \
		--build-arg APP_METADATA="$$(python $(SRCROOT)/y2j $(STAGE)/app_metadata.yaml)" \
		$(STAGE)

# This assumes that credentials for the aws tool are configured, either in
# ~/.aws/config or in AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
push: image $(BUILD_DIR)/container-tag
	  docker push $(DOCKER_REPOSITORY):$(IMAGE_TAG))

clean:
	rm -rf $(VENV)
	rm -rf $(STAGE)
	rm -rf $(SRCROOT)/dist
	rm -rf $(VAULTROOT)/dist
