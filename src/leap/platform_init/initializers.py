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
import stat
import subprocess
import tempfile

from PySide import QtGui

from leap.config.leapsettings import LeapSettings
from leap.services.eip import vpnlaunchers

logger = logging.getLogger(__name__)

# NOTE we could use a deferToThread here, but should
# be aware of this bug: http://www.themacaque.com/?p=1067


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

def _get_missing_updown_dialog():
    """
    Creates a dialog for notifying of missing updown scripts.
    Returns that dialog.

    :rtype: QtGui.QMessageBox instance
    """
    msg = QtGui.QMessageBox()
    msg.setWindowTitle(msg.tr("Missing up/down scripts"))
    msg.setText(msg.tr(
        "LEAPClient needs to install up/down scripts "
        "for Encrypted Internet to work properly. "
        "Would you like to proceed?"))
    msg.setInformativeText(msg.tr(
        "It looks like either you have not installed "
        "LEAP Client in a permanent location or you have an "
        "incomplete installation. This will ask for "
        "administrative privileges."))
    msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
    msg.addButton("No, don't ask again", QtGui.QMessageBox.RejectRole)
    msg.setDefaultButton(QtGui.QMessageBox.Yes)
    return msg

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
    logger.debug(
        'platform initializer check: has tun_and_startup = %s' %
        (has_tun_and_startup,))
    return has_tun_and_startup


def _darwin_install_missing_scripts(badexec, notfound):
    """
    Tries to install the missing up/down scripts.

    :param badexec: error for notifying execution error during command.
    :type badexec: str
    :param notfound: error for notifying missing path.
    :type notfound: str
    """
    # We expect to execute this from some way of bundle, since
    # the up/down scripts should be put in place by the installer.
    installer_path = os.path.join(
        os.getcwd(),
        "..",
        "Resources",
        "openvpn")
    launcher = vpnlaunchers.DarwinVPNLauncher
    if os.path.isdir(installer_path):
        tempscript = tempfile.mktemp()
        try:
            cmd = launcher.OSASCRIPT_BIN
            scriptlines = launcher.cmd_for_missing_scripts(installer_path)
            with open(tempscript, 'w') as f:
                f.write(scriptlines)
            st = os.stat(tempscript)
            os.chmod(tempscript, st.st_mode | stat.S_IEXEC | stat.S_IXUSR |
                     stat.S_IXGRP | stat.S_IXOTH)

            osascript = launcher.OSX_ASADMIN % ("/bin/sh %s" % (tempscript,),)
            cmdline = ["%s -e '%s'" % (cmd, osascript)]
            ret = subprocess.call(
                cmdline, stdout=subprocess.PIPE,
                shell=True)
            assert(ret)
        except Exception as exc:
            logger.error(badexec)
            logger.error("Error was: %r" % (exc,))
            f.close()
        finally:
            # XXX remove file
            pass
    else:
        logger.error(notfound)
        logger.debug('path searched: %s' % (installer_path,))


def DarwinInitializer():
    """
    Raises a dialog in case that the osx tuntap driver has not been found
    in the registry, asking the user for permission to install the driver
    """
    # XXX split this function into several

    NOTFOUND_MSG = ("Tried to install %s, but %s "
                    "not found inside this bundle.")
    BADEXEC_MSG = ("Tried to install %s, but %s "
                   "failed to %s.")

    TUNTAP_NOTFOUND_MSG = NOTFOUND_MSG % (
        "tuntaposx kext", "the installer")
    TUNTAP_BADEXEC_MSG = BADEXEC_MSG % (
        "tuntaposx kext", "the installer", "be launched")

    UPDOWN_NOTFOUND_MSG = NOTFOUND_MSG % (
        "updown scripts", "those were")
    UPDOWN_BADEXEC_MSG = BADEXEC_MSG % (
        "updown scripts", "they", "be copied")

    # TODO DRY this with other cases, and
    # factor out to _should_install() function.
    # Leave the dialog as a more generic thing.

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
            installer_path = os.path.join(
                os.getcwd(),
                "..",
                "Resources",
                "tuntap-installer.app")
            if os.path.isdir(installer_path):
                cmd = ["open %s" % (installer_path,)]
                try:
                    ret = subprocess.call(
                        cmd, stdout=subprocess.PIPE,
                        shell=True)
                except:
                    logger.error(TUNTAP_BADEXEC_MSG)
            else:
                logger.error(TUNTAP_NOTFOUND_MSG)

    config = LeapSettings()
    alert_missing = config.get_alert_missing_scripts()
    missing_scripts = vpnlaunchers.DarwinVPNLauncher.missing_updown_scripts
    if alert_missing and missing_scripts():
        msg = _get_missing_updown_dialog()
        ret = msg.exec_()

        if ret == QtGui.QMessageBox.Yes:
            _darwin_install_missing_scripts(
                UPDOWN_BADEXEC_MSG,
                UPDOWN_NOTFOUND_MSG)

        elif ret == QtGui.QMessageBox.No:
            logger.debug("Not installing missing scripts, "
                         "user decided to ignore our warning.")

        elif ret == QtGui.QMessageBox.Rejected:
            logger.debug(
                "Setting alert_missing_scripts to False, we will not "
                "ask again")
            config.set_alert_missing_scripts(False)
