#!/bin/bash

set -x

srcroot=$(cd `dirname $0`; pwd)

# firkinize must be a sibling directory to vouch
firkroot=$(cd $srcroot/../firkinize || exit 1; pwd)
if [ ! -d "$firkroot" ]; then
    echo "Firkinize must be available in $srcroot/../firkinize" 1>&2
    exit 1
fi

venv=$srcroot/.venv
virtualenv $venv
source $venv/bin/activate

# add both vouch and firkinize the .venv
pip install -e $srcroot -e $firkroot

# run the tests
python setup.py test
