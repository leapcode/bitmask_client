from __future__ import print_function
import logging
import time
logger = logging.getLogger(name=__name__)

from leap.base.network import NetworkChecker
from leap.baseapp.dialogs import ErrorDialog


class NetworkCheckerAppMixin(object):
    """
    initialize an instance of the Network Checker,
    which gathers error and passes them on.
    """

    def __init__(self, *args, **kwargs):
        opts = kwargs.pop('opts', None)
        config_file = getattr(opts, 'config_file', None)

        self.network_checker_started = False

        self.network_checker = NetworkChecker(
            watcher_cb=self.newLogLine.emit,
            status_signals=(self.statusChange.emit, ),
            debug=self.debugmode)

        self.network_checker.run_checks()
        self.error_check()

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


