from __future__ import print_function

import logging

logger = logging.getLogger(name=__name__)

from PyQt4 import QtCore

from leap.baseapp.dialogs import ErrorDialog
from leap.base.network import NetworkCheckerThread


class NetworkCheckerAppMixin(object):
    """
    initialize an instance of the Network Checker,
    which gathers error and passes them on.
    """

    def __init__(self, *args, **kwargs):
        provider = kwargs.pop('provider', None)
        self.network_checker = NetworkCheckerThread(
            error_cb=self.networkError.emit,
            debug=self.debugmode,
            provider=provider)

        # XXX move run_checks to slot -- this definitely
        # cannot start on init!!!
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
