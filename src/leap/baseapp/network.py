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
    def __init__(self, *args, **kwargs):
        provider = kwargs.pop('provider', None)
        if provider:
            self.init_network_checker(provider)

    def init_network_checker(self, provider):
        null_check(provider, "provider_domain")
        if not hasattr(self, 'network_checker'):
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
        logger.debug('handling network exception')
        logger.error(exc.message)
        dialog = ErrorDialog(parent=self)

        if exc.critical:
            dialog.criticalMessage(exc.usermessage, "network error")
        else:
            dialog.warningMessage(exc.usermessage, "network error")
