# -*- coding: utf-8 -*-
from __future__ import (print_function)
import logging
import threading

from leap.base.checks import LeapNetworkChecker
from leap.base.constants import ROUTE_CHECK_INTERVAL
from leap.base.exceptions import TunnelNotDefaultRouteError
from leap.util.coroutines import (launch_thread_no_daemon, process_events)

from time import sleep

logger = logging.getLogger(name=__name__)


class NetworkChecker(object):
    """
    Manages network checking thread that makes sure we have a working network
    connection.
    """
    def __init__(self, *args, **kwargs):
        self.status_signals = kwargs.pop('status_signals', None)
        self.watcher_cb = kwargs.pop('status_signals', None)
        self.excp_logger = lambda exc: logger.error("%s", exc.message)
        self.checker = LeapNetworkChecker()

    def start(self):
        self.process_handle = self._launch_recurrent_network_checks((self.excp_logger,))

    def stop(self):
        #TODO: Thread still not being stopped when openvpn is stopped.
        logger.debug("stopping network checker...")
        self.process_handle._Thread__stop()
        logger.debug("network checked stopped.")

    def run_checks(self):
        pass

    #private methods

    #here all the observers in fail_callbacks expect one positional argument,
    #which is exception so we can try by passing a lambda with logger to
    #check it works.
    def _network_checks_thread(self, fail_callbacks):
        #TODO: replace this with waiting for a signal from openvpn
        while True:
            try:
                self.checker.check_tunnel_default_interface()
                break
            except TunnelNotDefaultRouteError:
                sleep(1)

        observer_dict = dict(((
            observer, process_events(observer)) for observer in fail_callbacks))
        while True:
            try:
                self.checker.check_tunnel_default_interface()
                self.checker.check_internet_connection()
                sleep(ROUTE_CHECK_INTERVAL)
            except Exception as exc:
                for obs in observer_dict:
                    observer_dict[obs].send(exc)
                sleep(ROUTE_CHECK_INTERVAL)


    def _launch_recurrent_network_checks(self, fail_callbacks):
        #we need to wrap the fail callback in a turple
        watcher = launch_thread_no_daemon(
            self._network_checks_thread,
            (fail_callbacks,))
        return watcher


