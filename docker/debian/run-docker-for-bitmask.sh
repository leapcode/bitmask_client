#!/bin/sh
# NOTE: to get X11 socket forwarding to work we need this
xhost local:root

docker run --rm -it \
    --net host \
    --privileged \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e DISPLAY=unix$DISPLAY \
    -v `pwd`:/host/ \
    -p 1984:1984 -p 2013:2013 \
    ubuntu:vivid bash

# NOTE: what to do next?
# Install bitmask package:
# $ apt-bitmask.sh stable
# Install polkit agent (bitmask needs it):
# $ apt-get install lxpolkit
# Run polkit in background:
# $ lxpolkit &  # this will show you a message like: 'No session for pid 5801', ignore it
# Run bitmask:
# $ bitmask -d
