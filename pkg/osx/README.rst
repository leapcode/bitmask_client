environment setup in osx
========================

Requirements
============

pyinstaller
-----------
You need at least version 3.0.

pyside
----------
use repo branch kalikaneko/PySide (has --standalone patch)

python2.7 setup.py bdist_wheel --version=1.2.2 --standalone

Blockers
========
#7321 - requests bug in merge_environment_settings
