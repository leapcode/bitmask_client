# the problem of watching a stdout pipe from
# openvpn binary: using subprocess and coroutines
# acting as event consumers

from __future__ import division, print_function

import logging
from subprocess import PIPE, Popen
import sys
from threading import Thread

logger = logging.getLogger(__name__)

ON_POSIX = 'posix' in sys.builtin_module_names


#
# Coroutines goodies
#

def coroutine(func):
    def start(*args, **kwargs):
        cr = func(*args, **kwargs)
        cr.next()
        return cr
    return start


@coroutine
def process_events(callback):
    """
    coroutine loop that receives
    events sent and dispatch the callback.
    :param callback: callback to be called\
for each event
    :type callback: callable
    """
    try:
        while True:
            m = (yield)
            if callable(callback):
                callback(m)
            else:
                logger.debug('not a callable passed')
    except GeneratorExit:
        return

#
# Threads
#


def launch_thread(target, args):
    """
    launch and demonize thread.
    :param target: target function that will run in thread
    :type target: function
    :param args: args to be passed to thread
    :type args: list
    """
    t = Thread(target=target,
               args=args)
    t.daemon = True
    t.start()
    return t


def watch_output(out, observers):
    """
    initializes dict of observer coroutines
    and pushes lines to each of them as they are received
    from the watched output.
    :param out: stdout of a process.
    :type out: fd
    :param observers: tuple of coroutines to send data\
for each event
    :type observers: tuple
    """
    observer_dict = dict(((observer, process_events(observer))
                         for observer in observers))
    for line in iter(out.readline, b''):
        for obs in observer_dict:
            observer_dict[obs].send(line)
    out.close()


def spawn_and_watch_process(command, args, observers=None):
    """
    spawns a subprocess with command, args, and launch
    a watcher thread.
    :param command: command to be executed in the subprocess
    :type command: str
    :param args: arguments
    :type args: list
    :param observers: tuple of observer functions to be called \
for each line in the subprocess output.
    :type observers: tuple
    :return: a tuple containing the child process instance, and watcher_thread,
    :rtype: (Subprocess, Thread)
    """
    subp = Popen([command] + args,
                 stdout=PIPE,
                 stderr=PIPE,
                 bufsize=1,
                 close_fds=ON_POSIX)
    watcher = launch_thread(
        watch_output,
        (subp.stdout, observers))
    return subp, watcher
