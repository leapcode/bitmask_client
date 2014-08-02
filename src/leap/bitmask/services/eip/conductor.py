# -*- coding: utf-8 -*-
# conductor.py
# Copyright (C) 2014 LEAP
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
EIP Conductor module.
"""
import logging

from PySide import QtCore

from leap.bitmask.gui import statemachines
from leap.bitmask.services import EIP_SERVICE
from leap.bitmask.services import get_service_display_name
from leap.bitmask.services.eip.connection import EIPConnection
from leap.bitmask.platform_init import IS_MAC

QtDelayedCall = QtCore.QTimer.singleShot
logger = logging.getLogger(__name__)


class EIPConductor(object):

    def __init__(self, settings, backend, leap_signaler, **kwargs):
        """
        Initializes EIP Conductor.

        :param settings:
        :type settings:

        :param backend:
        :type backend:
        """
        self.eip_connection = EIPConnection()
        self.eip_name = get_service_display_name(EIP_SERVICE)
        self._settings = settings
        self._leap_signaler = leap_signaler
        self._backend = backend

        self._eip_status = None

    @property
    def qtsigs(self):
        return self.eip_connection.qtsigs

    def add_eip_widget(self, widget):
        """
        Keep a reference to the passed eip status widget.

        :param widget: the EIP Status widget.
        :type widget: QWidget
        """
        self._eip_status = widget

    def connect_signals(self):
        """
        Connect signals.
        """
        self.qtsigs.connecting_signal.connect(self._start_eip)

        self.qtsigs.disconnecting_signal.connect(self._stop_eip)
        self.qtsigs.disconnected_signal.connect(self._eip_status.eip_stopped)

    def connect_backend_signals(self):
        """
        Connect to backend signals.
        """
        signaler = self._leap_signaler

        # for conductor
        signaler.eip_process_restart_tls.connect(self._do_eip_restart)
        signaler.eip_process_restart_tls.connect(self._do_eip_failed)
        signaler.eip_process_restart_ping.connect(self._do_eip_restart)
        signaler.eip_process_finished.connect(self._eip_finished)

        # for widget
        self._eip_status.connect_backend_signals()

    def start_eip_machine(self, action):
        """
        Initializes and starts the EIP state machine.
        Needs the reference to the eip_status widget not to be empty.

        :action: QtAction
        """
        action = action
        button = self._eip_status.eip_button
        label = self._eip_status.eip_label

        builder = statemachines.ConnectionMachineBuilder(self.eip_connection)
        eip_machine = builder.make_machine(button=button,
                                           action=action,
                                           label=label)
        self.eip_machine = eip_machine
        self.eip_machine.start()
        logger.debug('eip machine started')

    def do_connect(self):
        """
        Start the connection procedure.
        Emits a signal that triggers the OFF -> Connecting sequence.
        This will call _start_eip via the state machine.
        """
        self.qtsigs.do_connect_signal.emit()

    def tear_fw_down(self):
        """
        Tear the firewall down.
        """
        self._backend.tear_fw_down()

    @QtCore.Slot()
    def _start_eip(self):
        """
        Starts EIP.
        """
        st = self._eip_status
        is_restart = st and st.is_restart

        def reconnect():
            self.qtsigs.disconnecting_signal.connect(self._stop_eip)

        if is_restart:
            QtDelayedCall(0, reconnect)
        else:
            self._eip_status.eip_pre_up()
        self.user_stopped_eip = False
        self.cancelled = False
        self._eip_status.hide_fw_down_button()

        # Until we set an option in the preferences window, we'll assume that
        # by default we try to autostart. If we switch it off manually, it
        # won't try the next time.
        self._settings.set_autostart_eip(True)
        self._eip_status.is_restart = False

        # DO the backend call!
        self._backend.eip_start(restart=is_restart)

    def reconnect_stop_signal(self):
        """
        Restore the original behaviour associated with the disconnecting
        signal, this is, trigger a normal stop, and not a restart one.
        """

        def do_stop(*args):
            self._stop_eip(restart=False)

        self.qtsigs.disconnecting_signal.disconnect()
        self.qtsigs.disconnecting_signal.connect(do_stop)

    @QtCore.Slot()
    def _stop_eip(self, restart=False, failed=False):
        """
        TRIGGERS:
          self.qsigs.do_disconnect_signal (via state machine)

        Stops vpn process and makes gui adjustments to reflect
        the change of state.

        :param restart: whether this is part of a eip restart.
        :type restart: bool

        :param failed: whether this is the final step of a retry sequence
        :type failed: bool
        """
        # XXX we should NOT keep status in the widget, but we do for a series
        # of hacks related to restarts. All status should be kept in a backend
        # object, widgets should be just widgets.
        self._eip_status.is_restart = restart
        self.user_stopped_eip = not restart and not failed

        def on_disconnected_do_restart():
            # hard restarts
            logger.debug("HARD RESTART")
            eip_status_label = self._eip_status.tr("{0} is restarting")
            eip_status_label = eip_status_label.format(self.eip_name)
            self._eip_status.eip_stopped(restart=True)
            self._eip_status.set_eip_status(eip_status_label, error=False)

            QtDelayedCall(2000, self.do_connect)

        def plug_restart_on_disconnected():
            self.qtsigs.disconnected_signal.connect(on_disconnected_do_restart)

        def reconnect_disconnected_signal():
            self.qtsigs.disconnected_signal.disconnect(
                on_disconnected_do_restart)

        def do_stop(*args):
            self._stop_eip(restart=False)

        if restart:
            # we bypass the on_eip_disconnected here
            plug_restart_on_disconnected()
            self.qtsigs.disconnected_signal.emit()
            # QtDelayedCall(0, self.qtsigs.disconnected_signal.emit)
            # ...and reconnect the original signal again, after having used the
            # diversion
            QtDelayedCall(500, reconnect_disconnected_signal)

        elif failed:
            self.qtsigs.disconnected_signal.emit()

        else:
            logger.debug('Setting autostart to: False')
            self._settings.set_autostart_eip(False)

        # Call to the backend.
        self._backend.eip_stop(restart=restart)

        # ... and inform the status widget
        self._eip_status.set_eipstatus_off(False)
        self._eip_status.eip_stopped(restart=restart, failed=failed)

        self._already_started_eip = False

        # XXX needed?
        if restart:
            QtDelayedCall(2000, self.reconnect_stop_signal)

    @QtCore.Slot()
    def _do_eip_restart(self):
        """
        TRIGGERS:
            self._eip_connection.qtsigs.process_restart

        Restart the connection.
        """
        if self._eip_status is not None:
            self._eip_status.is_restart = True

        def do_stop(*args):
            self._stop_eip(restart=True)

        try:
            self.qtsigs.disconnecting_signal.disconnect()
        except Exception:
            logger.error("cannot disconnect signals")

        self.qtsigs.disconnecting_signal.connect(do_stop)
        self.qtsigs.do_disconnect_signal.emit()

    @QtCore.Slot()
    def _do_eip_failed(self):
        """
        Stop EIP after a failure to start.

        TRIGGERS
            signaler.eip_process_restart_tls
        """
        logger.debug("TLS Error: eip_stop (failed)")
        self.qtsigs.connection_died_signal.emit()
        QtDelayedCall(1000, self._eip_status.eip_failed_to_connect)

    @QtCore.Slot(int)
    def _eip_finished(self, exitCode):
        """
        TRIGGERS:
            Signaler.eip_process_finished

        Triggered when the EIP/VPN process finishes to set the UI
        accordingly.

        Ideally we would have the right exit code here,
        but the use of different wrappers (pkexec, cocoasudo) swallows
        the openvpn exit code so we get zero exit in some cases  where we
        shouldn't. As a workaround we just use a flag to indicate
        a purposeful switch off, and mark everything else as unexpected.

        :param exitCode: the exit code of the eip process.
        :type exitCode: int
        """
        # TODO Add error catching to the openvpn log observer
        # so we can have a more precise idea of which type
        # of error did we have (server side, local problem, etc)

        logger.info("VPN process finished with exitCode %s..."
                    % (exitCode,))

        signal = self.qtsigs.disconnected_signal

        # XXX check if these exitCodes are pkexec/cocoasudo specific
        if exitCode in (126, 127):
            eip_status_label = self._eip_status.tr(
                "{0} could not be launched "
                "because you did not authenticate properly.")
            eip_status_label = eip_status_label.format(self.eip_name)
            self._eip_status.set_eip_status(eip_status_label, error=True)
            signal = self.qtsigs.connection_aborted_signal
            self._backend.eip_terminate()

        # XXX FIXME --- check exitcode is != 0 really.
        # bitmask-root is masking the exitcode, so we might need
        # to fix it on that side.
        # if exitCode != 0 and not self.user_stopped_eip:

        if not self.user_stopped_eip and not self.cancelled:
            error = True
            eip_status_label = self._eip_status.tr(
                "{0} finished in an unexpected manner!")
            eip_status_label = eip_status_label.format(self.eip_name)
            self._eip_status.set_eip_status_icon("error")
            self._eip_status.set_eip_status(eip_status_label,
                                            error=error)
            self._eip_status.eip_stopped()
            signal = self.qtsigs.connection_died_signal
            self._eip_status.show_fw_down_button()
            self._eip_status.eip_failed_to_connect()

        if self.cancelled:
            signal = self.qtsigs.connection_aborted_signal
            self._eip_status.set_eip_status_icon("error")
            self._eip_status.eip_stopped()
            self._eip_status.set_eip_status("", error=False)

        if exitCode == 0 and IS_MAC:
            # XXX remove this warning after I fix cocoasudo.
            logger.warning("The above exit code MIGHT BE WRONG.")

        # We emit signals to trigger transitions in the state machine:
        signal.emit()
