from __future__ import print_function

import logging
logger = logging.getLogger(name=__name__)

from leap.base.network import NetworkCheckerThread
#from leap.baseapp.dialogs import ErrorDialog


class NetworkCheckerAppMixin(object):
    """
    initialize an instance of the Network Checker,
    which gathers error and passes them on.
    """

    def __init__(self, *args, **kwargs):
        self.network_checker = NetworkCheckerThread(
            # XXX watcher? remove -----
            watcher_cb=self.newLogLine.emit,
            # XXX what callback? ------
            error_cb=None,
            debug=self.debugmode)

        # XXX move run_checks to slot
        self.network_checker.run_checks()
