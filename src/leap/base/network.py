# -*- coding: utf-8 -*-
from __future__ import (print_function)

from leap.base.checks import LeapNetworkChecker
from leap.base.constants import ROUTE_CHECK_INTERVAL
from leap.util.coroutines import (launch_thread, process_events)

from time import sleep

class NetworkChecker(object):
    """
    Manages network checking thread that makes sure we have a working network
    connection.
    """
    def __init__(self, *args, **kwargs):
        self.status_signals = kwargs.pop('status_signals', None)
        self.watcher_cb = kwargs.pop('status_signals', None)

    def start(self):
        self._launch_recurrent_network_checks((self.watcher_cb,))

    def stop(self):
        raise NotImplementedError

    def run_checks(self):
        pass

    #private methods

    #here all the observers in fail_callbacks expect one positional argument,
    #which is exception so we can try by passing a lambda with logger to
    #check it works.
    def _network_checks_thread(self, fail_callbacks):
        print('fail_callbacks: %s' % fail_callbacks)
        print(len(fail_callbacks))
        observer_dict = dict(((
            observer, process_events(observer)) for observer in fail_callbacks))
        netchecker = LeapNetworkChecker()
        while True:
            try:
                netchecker.check_internet_connection()
                sleep(ROUTE_CHECK_INTERVAL)
            except Exception as exc:
                for obs in observer_dict:
                    observer_dict[obs].send(exc)


    def _launch_recurrent_network_checks(fail_callbacks):
        print(type(fail_callbacks))
        watcher = launch_thread(
            network_checks_thread,
            (fail_callbacks,))
        return watcher


