#!/bin/bash
# Helper script to install, run and do a screenshot of bitmask

# You can use this as follows:
# $ docker run -t -i --rm -v `pwd`:/host/ ubuntu:14.04 /bin/bash
# $ cd /host/
# $ ./bitmask-on-docker.sh stable

[[ -z $1 ]] && exit 1

./apt-bitmask.sh $1 # this does an `apt-get update`
apt-get -y install xinit xvfb imagemagick lxpolkit

startx -- `which Xvfb` :1 -screen 0 1024x768x24 &
sleep 1

DISPLAY=:1 lxpolkit &
sleep 0.5 # bitmask needs polkit to work

DISPLAY=:1 bitmask &
sleep 2  # wait for bitmask to start

DISPLAY=:1 import -window root bitmask.png
