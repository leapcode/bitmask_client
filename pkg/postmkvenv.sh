#!/bin/bash
# This hook is run after a new virtualenv is activated.
# ~/.virtualenvs/postmkvirtualenv

# Symlinks PyQt4 from global installation into virtualenv site-packages

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
