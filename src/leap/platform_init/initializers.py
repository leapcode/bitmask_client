# -*- coding: utf-8 -*-
# initializers.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Platform dependant initializing code
"""

import logging
import os
import platform
import subprocess

from PySide import QtGui

logger = logging.getLogger(__name__)


def init_platform():
    initializer = None
    try:
        initializer = globals()[platform.system() + "Initializer"]
    except:
        pass
    if initializer:
        logger.debug("Running initializer for %s" % (platform.system(),))
        initializer()
    else:
        logger.debug("Initializer not found for %s" % (platform.system(),))


def _windows_has_tap_device():
    import _winreg as reg

    adapter_key = 'SYSTEM\CurrentControlSet\Control\Class' \
        '\{4D36E972-E325-11CE-BFC1-08002BE10318}'
    with reg.OpenKey(reg.HKEY_LOCAL_MACHINE, adapter_key) as adapters:
        try:
            for i in xrange(10000):
                key_name = reg.EnumKey(adapters, i)
                with reg.OpenKey(adapters, key_name) as adapter:
                    try:
                        component_id = reg.QueryValueEx(adapter,
                                                        'ComponentId')[0]
                        if component_id.startswith("tap0901"):
                            return True
                    except WindowsError:
                        pass
        except WindowsError:
            pass
    return False


def WindowsInitializer():
    if not _windows_has_tap_device():
        msg = QtGui.QMessageBox()
        msg.setWindowTitle(msg.tr("TAP Driver"))
        msg.setText(msg.tr("LEAPClient needs to install the necessary drivers "
                           "for Encrypted Internet to work. Would you like to "
                           "proceed?"))
        msg.setInformativeText(msg.tr("Encrypted Internet uses VPN, which "
                                      "needs a TAP device installed and none "
                                      "has been found"))
        msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        msg.setDefaultButton(QtGui.QMessageBox.Yes)
        ret = msg.exec_()

        if ret == QtGui.QMessageBox.Yes:
            driver_path = os.path.join(os.getcwd(),
                                       "apps",
                                       "eip",
                                       "tap_driver")
            dev_installer = os.path.join(driver_path,
                                         "devcon.exe")
            if os.path.isfile(dev_installer) and \
                    os.access(dev_installer, os.X_OK):
                inf_path = os.path.join(driver_path,
                                        "OemWin2k.inf")
                cmd = [dev_installer, "install", inf_path, "tap0901"]
                ret = subprocess.call(cmd, stdout=subprocess.PIPE, shell=True)
            else:
                logger.error("Tried to install TAP driver, but the installer "
                             "is not found or not executable")
