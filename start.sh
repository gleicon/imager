#!/bin/bash
# see scripts/debian-init.d for production deployments

cd `dirname $0`
export PYTHONPATH=`dirname $0`
twistd -n cyclone -p 8888 -l 0.0.0.0 \
       -r imager.web.Application -c imager.conf $*
