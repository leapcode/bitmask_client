import logging
import time

from PyQt4 import QtCore

from leap.baseapp.dialogs import ErrorDialog
from leap.baseapp import constants
from leap.eip import exceptions as eip_exceptions
from leap.eip.eipconnection import EIPConnection

logger = logging.getLogger(name=__name__)


class EIPConductorApp(object):
    # XXX EIPConductorMixin ?
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
            status_signals=(self.statusChange.emit, ),
            debug=self.debugmode)

        # XXX remove skip download when sample service is ready
        self.conductor.run_checks(skip_download=True)
        self.error_check()

        # XXX should receive "ready" signal
        # it is called from LeapWindow now.
        #if self.conductor.autostart:
            #self.start_or_stopVPN()

        if self.debugmode:
            self.startStopButton.clicked.connect(
                lambda: self.start_or_stopVPN())

    def error_check(self):
        logger.debug('error check')

        #####################################
        # XXX refactor in progress (by #504)
        errq = self.conductor.error_queue
        while errq.qsize() != 0:
            logger.debug('%s errors left in conductor queue', errq.qsize())
            error = errq.get()
            logger.error('%s: %s', error.__class__.__name__, error.message)

            if issubclass(error.__class__, eip_exceptions.EIPClientError):
                if error.critical:
                    logger.critical(error.message)
                    logger.error('quitting')

                    # XXX
                    # check headless = False before
                    # launching dialog.
                    # (for Qt tests)

                    dialog = ErrorDialog()
                    if getattr(error, 'usermessage', None):
                        message = error.usermessage
                    else:
                        message = error.message
                    dialog.criticalMessage(message, 'error')
                else:
                    logger.exception(error.message)
            else:
                import traceback
                traceback.print_exc()
                raise error

        if self.conductor.missing_definition is True:
            dialog = ErrorDialog()
            dialog.criticalMessage(
                'The default '
                'definition.json file cannot be found',
                'error')

        if self.conductor.missing_provider is True:
            dialog = ErrorDialog()
            dialog.criticalMessage(
                'Missing provider. Add a remote_ip entry '
                'under section [provider] in eip.cfg',
                'error')

        if self.conductor.missing_vpn_keyfile is True:
            dialog = ErrorDialog()
            dialog.criticalMessage(
                'Could not find the vpn keys file',
                'error')

        # ... btw, review pending.
        # os.kill of subprocess fails if we have
        # some of this errors.

        # deprecated.
        # get something alike.
        #if self.conductor.bad_provider is True:
            #dialog = ErrorDialog()
            #dialog.criticalMessage(
                #'Bad provider entry. Check that remote_ip entry '
                #'has an IP under section [provider] in eip.cfg',
                #'error')

        if self.conductor.bad_keyfile_perms is True:
            dialog = ErrorDialog()
            dialog.criticalMessage(
                'The vpn keys file has bad permissions',
                'error')

        if self.conductor.missing_pkexec is True:
            dialog = ErrorDialog()
            dialog.warningMessage(
                'We could not find <b>pkexec</b> in your '
                'system.<br/> Do you want to try '
                '<b>setuid workaround</b>? '
                '(<i>DOES NOTHING YET</i>)',
                'error')

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
            return

        if self.conductor.with_errors:
            #XXX how to wait on pkexec???
            #something better that this workaround, plz!!
            time.sleep(5)
            logger.debug('timeout')
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
        if self.eip_service_started is False:
            try:
                self.conductor.connect()
                # XXX move this to error queue
            except eip_exceptions.EIPNoCommandError:
                dialog = ErrorDialog()
                dialog.warningMessage(
                    'No suitable openvpn command found. '
                    '<br/>(Might be a permissions problem)',
                    'error')
            if self.debugmode:
                self.startStopButton.setText('&Disconnect')
            self.eip_service_started = True

            # XXX what is optimum polling interval?
            # too little is overkill, too much
            # will miss transition states..

            # XXX decouple! (timer is init by icons class).
            # should bring it here?
            # to its own class?

            self.timer.start(constants.TIMER_MILLISECONDS)
            return

        if self.eip_service_started is True:
            self.conductor.disconnect()
            if self.debugmode:
                self.startStopButton.setText('&Connect')
            self.eip_service_started = False
            self.timer.stop()
            return
