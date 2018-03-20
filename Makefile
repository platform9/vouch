
.SUFFIXES:
.PHONY: clean push image stage dist unit-test

SRCROOT = $(abspath $(dir $(CURDIR)/$(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))))
BUILD_DIR := $(SRCROOT)/build
VENV := $(SRCROOT)/.venv
STAGE = $(BUILD_DIR)/container
$(shell mkdir -p $(STAGE))

VOUCH_CODE = $(shell find $(SRCROOT)/vouch -name '*.py') $(SRCROOT)/setup.py
VOUCH_DIST = $(STAGE)/vouch-sdist.tgz

FIRKINROOT = $(abspath $(SRCROOT)/../firkinize)
FIRKIN_CODE = $(shell find $(FIRKINROOT)/firkinize -name '*.py') \
              $(FIRKINROOT)/setup.py
FIRKIN_DIST = $(STAGE)/firkinize-sdist.tgz

BUILD_NUMBER ?= 0
PF9_VERSION ?= 0.0.0
DOCKER_REPOSITORY ?= 514845858982.dkr.ecr.us-west-1.amazonaws.com/vouch
BUILD_ID := $(BUILD_NUMBER)
IMAGE_TAG ?= "$(or $(PF9_VERSION), $(PF9_VERSION), "latest")-$(BUILD_ID)"
BRANCH_NAME ?= $(or $(TEAMCITY_BUILD_BRANCH), $(TEAMCITY_BUILD_BRANCH), $(shell git symbolic-ref --short HEAD))

dist: $(VOUCH_DIST) $(FIRKIN_DIST)

$(VOUCH_DIST): $(VOUCH_CODE)
	cd $(SRCROOT) && \
	rm -f dist/vouch* && \
	python setup.py sdist && \
	cp dist/vouch* $@

$(FIRKIN_DIST): $(FIRKIN_CODE)
	cd $(FIRKINROOT) && \
	rm -f dist/firkin* && \
	python setup.py sdist && \
	cp dist/firkin* $@

stage: dist
	cp -r $(SRCROOT)/container/* $(STAGE)/

$(BUILD_DIR):
	mkdir -p $@

$(BUILD_DIR)/container-tag: $(BUILD_DIR)
	echo -ne "$(IMAGE_TAG)" >$@

unit-test:
	(test -d $(VENV) || virtualenv $(VENV)) && \
	$(VENV)/bin/python $(VENV)/bin/pip install -e$(SRCROOT) -e$(FIRKINROOT) nose && \
	$(VENV)/bin/nosetests -vd .

$(VENV)/bin/y2j:
	(test -d $(VENV) || virtualenv $(VENV)) && \
	$(VENV)/bin/python $(VENV)/bin/pip install -e$(FIRKINROOT)

image: stage $(VENV)/bin/y2j
	docker build -t $(DOCKER_REPOSITORY):$(IMAGE_TAG) \
		--build-arg BUILD_ID=$(BUILD_ID) \
		--build-arg VERSION=$(PF9_VERSION) \
		--build-arg BRANCH=$(BRANCH_NAME) \
		--build-arg APP_METADATA="$$($(VENV)/bin/y2j $(STAGE)/app_metadata.yaml)" \
		$(STAGE)

# This assumes that credentials for the aws tool are configured, either in
# ~/.aws/config or in AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
push: image $(BUILD_DIR)/container-tag
	docker push $(DOCKER_REPOSITORY):$(IMAGE_TAG) || \
	(aws ecr get-login --region=us-west-1 |sh && \
		docker push $(DOCKER_REPOSITORY):$(IMAGE_TAG))

clean:
	rm -rf $(STAGE)
	rm -rf $(SRCROOT)/dist
	rm -rf $(FIRKINROOT)/dist
