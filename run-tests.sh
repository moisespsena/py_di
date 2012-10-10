#!/bin/bash

PYTHONS='
python2.7
python3.2
'

_ci() {
    echo -e "\033[34;1m[INFO] ${1}\033[m"
}
_ce() {
    echo -e "\033[31;1m[ERROR] ${1}\033[m" 1>&2
}

ag="$@"

_cmd() {
    [ `which "$1"` ] && {
	_ci "================================== $1 ===================================="
        _ci "$1 test"
	"$1" setup.py test
    } || _ce "$1 not found"
}

echo "$PYTHONS" | while read l; do [ "$l" != "" ] && _cmd "$l"; done
