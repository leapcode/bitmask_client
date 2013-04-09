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
    """
    Returns the right initializer for the platform we are running in, or
    None if no proper initializer is found
    """
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
    """
    Loops over the windows registry trying to find if the tap0901 tap driver
    has been installed on this machine.
    """
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
    """
    Raises a dialog in case that the windows tap driver has not been found
    in the registry, asking the user for permission to install the driver
    """
    if not _windows_has_tap_device():
        msg = QtGui.QMessageBox()
        msg.setWindowTitle(msg.tr("TAP Driver"))
        msg.setText(msg.tr("LEAPClient needs to install the necessary drivers "
                           "for Encrypted Internet to work. Would you like to "
                           "proceed?"))
        msg.setInformativeText(msg.tr("Encrypted Internet uses VPN, which "
                                      "needs a TAP device installed and none "
                                      "has been found. This will ask for "
                                      "administrative privileges."))
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
                # XXX should avoid shell expansion.
                ret = subprocess.call(cmd, stdout=subprocess.PIPE, shell=True)
            else:
                logger.error("Tried to install TAP driver, but the installer "
                             "is not found or not executable")


def _darwin_has_tun_kext():
    """
    Returns True only if we found a directory under the system kext folder
    containing a kext named tun.kext, AND we found a startup item named 'tun'
    """
    # XXX we should be smarter here and use kextstats output.

    has_kext = os.path.isdir("/System/Library/Extensions/tun.kext")
    has_startup = os.path.isdir("/System/Library/StartupItems/tun")
    has_tun_and_startup = has_kext and has_startup
    logger.debug('platform initializer check: has tun_and_startup = %s' %
            (has_tun_and_startup,))
    return has_tun_and_startup


def DarwinInitializer():
    """
    Raises a dialog in case that the osx tuntap driver has not been found
    in the registry, asking the user for permission to install the driver
    """
    NOTFOUND_MSG = ("Tried to install tuntaposx kext, but the installer "
                    "is not found inside this bundle.")
    BADEXEC_MSG = ("Tried to install tuntaposx kext, but the installer "
                   "failed to be launched.")
    if not _darwin_has_tun_kext():
        msg = QtGui.QMessageBox()
        msg.setWindowTitle(msg.tr("TUN Driver"))
        msg.setText(msg.tr("LEAPClient needs to install the necessary drivers "
                           "for Encrypted Internet to work. Would you like to "
                           "proceed?"))
        msg.setInformativeText(msg.tr("Encrypted Internet uses VPN, which "
                                      "needs a kernel extension for a TUN "
                                      "device installed, and none "
                                      "has been found. This will ask for "
                                      "administrative privileges."))
        msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        msg.setDefaultButton(QtGui.QMessageBox.Yes)
        ret = msg.exec_()

        if ret == QtGui.QMessageBox.Yes:
            installer_path = os.path.join(os.getcwd(),
                                       "..",
                                       "Resources",
                                       "tuntap-installer.app")
            if os.path.isdir(installer_path):
                cmd = ["open %s" % (installer_path,)]
                try:
                    # XXX should avoid shell expansion
                    ret = subprocess.call(
                        cmd, stdout=subprocess.PIPE,
                        shell=True)
                except:
                    logger.error(BADEXEC_MSG)
            else:
                logger.error(NOTFOUND_MSG)
