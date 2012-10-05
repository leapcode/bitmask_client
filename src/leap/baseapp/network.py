from __future__ import print_function

import logging
logger = logging.getLogger(name=__name__)

from leap.base.network import NetworkChecker
#from leap.baseapp.dialogs import ErrorDialog


class NetworkCheckerAppMixin(object):
    """
    initialize an instance of the Network Checker,
    which gathers error and passes them on.
    """

    def __init__(self, *args, **kwargs):
        self.network_checker = NetworkChecker(
            watcher_cb=self.newLogLine.emit,
            error_cb=self.handle_network_error,
            debug=self.debugmode)

        self.network_checker.run_checks()
