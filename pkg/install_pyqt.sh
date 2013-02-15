#!/bin/sh
pip install sip  # fails
cd build/sip
python configure.py
make && make install
cd ../..
pip install PyQt  # fails
cd build/PyQt
python configure.py
make && make install
