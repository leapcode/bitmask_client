from __future__ import print_function
import logging
import time
#import sys

from PyQt4 import QtCore

from leap.baseapp.dialogs import ErrorDialog
from leap.baseapp import constants
from leap.eip import exceptions as eip_exceptions
from leap.eip.eipconnection import EIPConnection

logger = logging.getLogger(name=__name__)


class EIPConductorAppMixin(object):
    """
    initializes an instance of EIPConnection,
    gathers errors, and passes status-change signals
    from Qt land along to the conductor.
    Connects the eip connect/disconnect logic
    to the switches in the app (buttons/menu items).
    """

    def __init__(self, *args, **kwargs):
        opts = kwargs.pop('opts')
        config_file = getattr(opts, 'config_file', None)

        self.eip_service_started = False

        # conductor (eip connection) is in charge of all
        # vpn-related configuration / monitoring.
        # we pass a tuple of signals that will be
        # triggered when status changes.

        self.conductor = EIPConnection(
            watcher_cb=self.newLogLine.emit,
            config_file=config_file,
            checker_signals=(self.changeLeapStatus.emit, ),
            status_signals=(self.statusChange.emit, ),
            debug=self.debugmode,
            ovpn_verbosity=opts.openvpn_verb)

        self.skip_download = opts.no_provider_checks
        self.skip_verify = opts.no_ca_verify

    def run_eip_checks(self):
        """
        runs eip checks and
        the error checking loop
        """
        logger.debug('running EIP CHECKS')
        self.conductor.run_checks(
            skip_download=self.skip_download,
            skip_verify=self.skip_verify)
        self.error_check()

        # XXX should send ready signal instead
        if self.conductor.autostart:
            self.start_or_stopVPN()

    def error_check(self):
        """
        consumes the conductor error queue.
        pops errors, and acts accordingly (launching user dialogs).
        """
        logger.debug('error check')

        errq = self.conductor.error_queue
        while errq.qsize() != 0:
            logger.debug('%s errors left in conductor queue', errq.qsize())
            # we get exception and original traceback from queue
            error, tb = errq.get()

            # redundant log, debugging the loop.
            logger.error('%s: %s', error.__class__.__name__, error.message)

            if issubclass(error.__class__, eip_exceptions.EIPClientError):
                self.handle_eip_error(error)

            else:
                # deprecated form of raising exception.
                raise error, None, tb

            if error.failfirst is True:
                break

        #############################################
        # old errors to check
        # write test for them and them remove
        # their corpses from here.

        #if self.conductor.missing_vpn_keyfile is True:
            #dialog = ErrorDialog()
            #dialog.criticalMessage(
                #'Could not find the vpn keys file',
                #'error')

        #if self.conductor.bad_keyfile_perms is True:
            #dialog = ErrorDialog()
            #dialog.criticalMessage(
                #'The vpn keys file has bad permissions',
                #'error')

        # deprecated. configchecker takes care of that.
        #if self.conductor.missing_definition is True:
            #dialog = ErrorDialog()
            #dialog.criticalMessage(
                #'The default '
                #'definition.json file cannot be found',
                #'error')

    def handle_eip_error(self, error):
        """
        check severity and launches
        dialogs informing user about the errors.
        in the future we plan to derive errors to
        our log viewer.
        """

        if getattr(error, 'usermessage', None):
            message = error.usermessage
        else:
            message = error.message

        # XXX
        # check headless = False before
        # launching dialog.
        # (so Qt tests can assert stuff)

        if error.critical:
            logger.critical(error.message)
            #critical error (non recoverable),
            #we give user some info and quit.
            #(critical error dialog will exit app)
            ErrorDialog(errtype="critical",
                        msg=message,
                        label="critical error")
        elif error.warning:
            logger.warning(error.message)

        else:
            dialog = ErrorDialog()
            dialog.warningMessage(message, 'error')

    @QtCore.pyqtSlot()
    def statusUpdate(self):
        """
        polls status and updates ui with real time
        info about transferred bytes / connection state.
        right now is triggered by a timer tick
        (timer controlled by StatusAwareTrayIcon class)
        """
        # TODO I guess it's too expensive to poll
        # continously. move to signal events instead.
        # (i.e., subscribe to connection status changes
        # from openvpn manager)

        if not self.eip_service_started:
            # there is a race condition
            # going on here. Depending on how long we take
            # to init the qt app, the management socket
            # is not ready yet.
            return

        if self.conductor.with_errors:
            #XXX how to wait on pkexec???
            #something better that this workaround, plz!!
            #I removed the pkexec pass authentication at all.
            #time.sleep(5)
            #logger.debug('timeout')
            logger.error('errors. disconnect')
            self.start_or_stopVPN()  # is stop

        state = self.conductor.poll_connection_state()
        if not state:
            return

        ts, con_status, ok, ip, remote = state
        self.set_statusbarMessage(con_status)
        self.setIconToolTip()

        ts = time.strftime("%a %b %d %X", ts)
        if self.debugmode:
            self.updateTS.setText(ts)
            self.status_label.setText(con_status)
            self.ip_label.setText(ip)
            self.remote_label.setText(remote)

        # status i/o

        status = self.conductor.get_status_io()
        if status and self.debugmode:
            #XXX move this to systray menu indicators
            ts, (tun_read, tun_write, tcp_read, tcp_write, auth_read) = status
            ts = time.strftime("%a %b %d %X", ts)
            self.updateTS.setText(ts)
            self.tun_read_bytes.setText(tun_read)
            self.tun_write_bytes.setText(tun_write)

    @QtCore.pyqtSlot()
    def start_or_stopVPN(self):
        """
        stub for running child process with vpn
        """
        if self.conductor.has_errors():
            logger.debug('not starting vpn; conductor has errors')

        if self.eip_service_started is False:
            try:
                self.conductor.connect()

            except eip_exceptions.EIPNoCommandError as exc:
                self.handle_eip_error(exc)

            except Exception as err:
                # raise generic exception (Bad Thing Happened?)
                logger.exception(err)
            else:
                # no errors, so go on.
                if self.debugmode:
                    self.startStopButton.setText('&Disconnect')
                self.eip_service_started = True
                self.toggleEIPAct()

                # XXX decouple! (timer is init by icons class).
                # we could bring Timer Init to this Mixin
                # or to its own Mixin.
                self.timer.start(constants.TIMER_MILLISECONDS)
                self.network_checker.start()
            return

        if self.eip_service_started is True:
            self.network_checker.stop()
            self.conductor.disconnect()
            if self.debugmode:
                self.startStopButton.setText('&Connect')
            self.eip_service_started = False
            self.toggleEIPAct()
            self.timer.stop()
            return
