"""
Base Connection Classs
"""
from __future__ import (division, unicode_literals, print_function)

import logging

from leap.base.authentication import Authentication

logger = logging.getLogger(name=__name__)


class Connection(Authentication):
    # JSONLeapConfig
    #spec = {}

    def __init__(self, *args, **kwargs):
        self.connection_state = None
        self.desired_connection_state = None
        #XXX FIXME diamond inheritance gotcha..
        #If you inherit from >1 class,
        #super is only initializing one
        #of the bases..!!
        # I think we better pass config as a constructor
        # parameter -- kali 2012-08-30 04:33
        super(Connection, self).__init__(*args, **kwargs)

    def connect(self):
        """
        entry point for connection process
        """
        pass

    def disconnect(self):
        """
        disconnects client
        """
        pass

    def shutdown(self):
        """
        shutdown and quit
        """
        self.desired_con_state = self.status.DISCONNECTED

    def connection_state(self):
        """
        returns the current connection state
        """
        return self.status.current

    def desired_connection_state(self):
        """
        returns the desired_connection state
        """
        return self.desired_connection_state

    def get_icon_name(self):
        """
        get icon name from status object
        """
        return self.status.get_state_icon()

    #
    # private methods
    #

    def _disconnect(self):
        """
        private method for disconnecting
        """
        if self.subp is not None:
            self.subp.terminate()
            self.subp = None
        # XXX signal state changes! :)

    def _is_alive(self):
        """
        don't know yet
        """
        pass

    def _connect(self):
        """
        entry point for connection cascade methods.
        """
        #conn_result = ConState.DISCONNECTED
        try:
            conn_result = self._try_connection()
        except UnrecoverableError as except_msg:
            logger.error("FATAL: %s" % unicode(except_msg))
            conn_result = self.status.UNRECOVERABLE
        except Exception as except_msg:
            self.error_queue.append(except_msg)
            logger.error("Failed Connection: %s" %
                         unicode(except_msg))
        return conn_result


class ConnectionError(Exception):
    """
    generic connection error
    """
    def __str__(self):
        if len(self.args) >= 1:
            return repr(self.args[0])
        else:
            raise self()


class UnrecoverableError(ConnectionError):
    """
    we cannot do anything about it, sorry
    """
    pass
