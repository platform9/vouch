#!/bin/bash

set -xue

cd /buildroot/vouch && make --max-load=$(nproc) stage-with-py-container
