from __future__ import print_function

import logging

logger = logging.getLogger(name=__name__)

from PyQt4 import QtCore

from leap.baseapp.dialogs import ErrorDialog
from leap.base.network import NetworkCheckerThread

from leap.util.misc import null_check


class NetworkCheckerAppMixin(object):
    """
    initialize an instance of the Network Checker,
    which gathers error and passes them on.
    """
    ERR_NETERR = False

    def __init__(self, *args, **kwargs):
        provider = kwargs.pop('provider', None)
        self.network_checker = None
        if provider:
            self.init_network_checker(provider)

    def init_network_checker(self, provider):
        null_check(provider, "provider_domain")
        if not self.network_checker:
            self.network_checker = NetworkCheckerThread(
                error_cb=self.networkError.emit,
                debug=self.debugmode,
                provider=provider)
        self.network_checker.start()

    @QtCore.pyqtSlot(object)
    def runNetworkChecks(self):
        self.network_checker.run_checks()

    @QtCore.pyqtSlot(object)
    def onNetworkError(self, exc):
        """
        slot that receives a network exceptions
        and raises a user error message
        """
        # FIXME this should not HANDLE anything after
        # the network check thread has been stopped.

        logger.debug('handling network exception')
        if not self.ERR_NETERR:
            self.ERR_NETERR = True

            logger.error(exc.message)
            dialog = ErrorDialog(parent=self)
            if exc.critical:
                dialog.criticalMessage(exc.usermessage, "network error")
            else:
                dialog.warningMessage(exc.usermessage, "network error")

            self.start_or_stopVPN()
            self.network_checker.stop()
