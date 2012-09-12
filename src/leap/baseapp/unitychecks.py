#!/usr/bin/python2
# vim: tabstop=8 expandtab shiftwidth=5 softtabstop=4
"""
modified from code from the starcal2 project
copyright Saeed Rasooli
License: GPL
"""
import logging
import platform
import sys
from subprocess import Popen, PIPE

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

from leap.base.constants import APP_NAME
from leap.baseapp.dialogs import ErrorDialog

get_whitelist = lambda: eval(Popen(['gsettings', 'get', 'com.canonical.Unity.Panel', 'systray-whitelist'], stdout=PIPE).communicate()[0])

set_whitelist = lambda ls: Popen(['gsettings', 'set', 'com.canonical.Unity.Panel', 'systray-whitelist', repr(ls)])

def add_to_whitelist():
    ls = get_whitelist()
    if not APP_NAME in ls:
        ls.append(APP_NAME)
        set_whitelist(ls)

def remove_from_whitelist():
    ls = get_whitelist()
    if APP_NAME in ls:
        ls.remove(APP_NAME)
        set_whitelist(ls)

def is_unity_running():
    (output, error) = Popen('ps aux | grep [u]nity-panel-service', stdout=PIPE, shell=True).communicate()
    output = bool(str(output))
    if not output:
        (output, error) = Popen('ps aux | grep [u]nity-2d-panel', stdout=PIPE, shell=True).communicate()
        output = bool(str(output))
    return output

def need_to_add():	
    if is_unity_running():
        wlist = get_whitelist()
        if not (APP_NAME in wlist or 'all' in wlist):
            logger.debug('need to add')
            return True
    return False

def add_and_restart():
    add_to_whitelist()
    Popen('LANG=en_US.UTF-8 unity', shell=True)

MSG = "Seems that you are using a Unity desktop and Leap is not allowed to use Tray icon. Press OK to add Leap to Unity's white list and then restart Unity"

def do_check():
    if platform.system() == "Linux" and need_to_add():
        dialog = ErrorDialog()
        dialog.confirmMessage(
            MSG,
            "add to systray?",
            add_and_restart)

if __name__=='__main__':
    if len(sys.argv)>1:
        cmd = sys.argv[1]
        if cmd=='add':
            add_to_whitelist()
        elif cmd=='rm':
            remove_from_whitelist()
        elif cmd=='print':
            print get_whitelist()
        elif cmd=="check":
            from PyQt4.QtGui import QApplication
            app = QApplication(sys.argv)
            do_check()

