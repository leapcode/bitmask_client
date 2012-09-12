#!/bin/bash
# This hook is run after a new virtualenv is activated.
# ~/.virtualenvs/postmkvirtualenv
# tested and working in debian

# Symlinks PyQt4 from global installation into virtualenv site-packages
# XXX TODO:
# script fails in ubuntu, with path: /usr/lib/pymodules/python2.7/PyQt4
# use import PyQt4; PyQt4.__path__ instead

LIBS=( PyQt4 sip.so )

PYTHON_VERSION=python$(python -c "import sys; print (str(sys.version_info[0])+'.'+str(sys.version_info[1]))")
VAR=( $(which -a $PYTHON_VERSION) )

GET_PYTHON_LIB_CMD="from distutils.sysconfig import get_python_lib; print (get_python_lib())"
LIB_VIRTUALENV_PATH=$(python -c "$GET_PYTHON_LIB_CMD")
LIB_SYSTEM_PATH=$(${VAR[-1]} -c "$GET_PYTHON_LIB_CMD")

for LIB in ${LIBS[@]}
do
    ln -s $LIB_SYSTEM_PATH/$LIB $LIB_VIRTUALENV_PATH/$LIB 
done
