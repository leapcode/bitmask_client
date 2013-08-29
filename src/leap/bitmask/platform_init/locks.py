# -*- coding: utf-8 -*-
# locks.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Utilities for handling multi-platform file locking mechanisms
"""
import logging
import errno
import os
import platform

from leap.bitmask import platform_init
from leap.common.events import signal as signal_event
from leap.common.events import events_pb2 as proto

if platform_init.IS_UNIX:
    from fcntl import flock, LOCK_EX, LOCK_NB
else:  # WINDOWS
    import datetime
    import glob
    import shutil
    import time

    from tempfile import gettempdir

    from leap.bitmask.util import get_modification_ts, update_modification_ts

logger = logging.getLogger(__name__)

if platform_init.IS_UNIX:

    class UnixLock(object):
        """
        Uses flock to get an exclusive lock over a file.
        See man 2 flock
        """

        def __init__(self, path):
            """
            iniializes t he UnixLock with the path of the
            desired lockfile
            """

            self._fd = None
            self.path = path

        def get_lock(self):
            """
            Tries to get a lock, and writes the running pid there if successful
            """
            gotit, pid = self._get_lock_and_pid()
            return gotit

        def get_pid(self):
            """
            Returns the pid of the locking process
            """
            gotit, pid = self._get_lock_and_pid()
            return pid

        def _get_lock(self):
            """
            Tries to get a lock, returning True if successful

            :rtype: bool
            """
            self._fd = os.open(self.path, os.O_CREAT | os.O_RDWR)

            try:
                flock(self._fd, LOCK_EX | LOCK_NB)
            except IOError as exc:
                # could not get the lock
                #import ipdb; ipdb.set_trace()

                if exc.args[0] in (errno.EDEADLK, errno.EAGAIN):
                    # errno 11 or 35
                    # Resource temporarily unavailable
                    return False
                else:
                    raise
            return True

        @property
        def locked_by_us(self):
            """
            Returns True if the pid in the pidfile
            is ours.

            :rtype: bool
            """
            gotit, pid = self._get_lock_and_pid()
            return pid == os.getpid()

        def _get_lock_and_pid(self):
            """
            Tries to get a lock over the file.
            Returns (locked, pid) tuple.

            :rtype: tuple
            """

            if self._get_lock():
                self._write_to_pidfile()
                return True, None

            return False, self._read_from_pidfile()

        def _read_from_pidfile(self):
            """
            Tries to read pid from the pidfile,
            returns False if no content found.
            """

            pidfile = os.read(
                self._fd, 16)
            if not pidfile:
                return False

            try:
                return int(pidfile.strip())
            except Exception as exc:
                exc.args += (pidfile, self.lock_file)
                raise

        def _write_to_pidfile(self):
            """
            Writes the pid of the running process
            to the pidfile
            """
            fd = self._fd
            os.ftruncate(fd, 0)
            os.write(fd, '%d\n' % os.getpid())
            os.fsync(fd)


if platform_init.IS_WIN:

    # Time to wait (in secs) before assuming a raise window signal has not been
    # ack-ed.

    RAISE_WINDOW_TIMEOUT = 2

    # How many steps to do while checking lockfile ts update.

    RAISE_WINDOW_WAIT_STEPS = 10

    def _release_lock(name):
        """
        Tries to remove a folder path.

        :param name: folder lock to remove
        :type name: str
        """
        try:
            shutil.rmtree(name)
            return True
        except WindowsError as exc:
            if exc.errno in (errno.EPIPE, errno.ENOENT,
                             errno.ESRCH, errno.EACCES):
                logger.warning(
                    'exception while trying to remove the lockfile dir')
                logger.warning('errno %s: %s' % (exc.errno, exc.args[1]))
                # path does not exist
                return False
            else:
                logger.debug('errno = %s' % (exc.errno,))
                # we did not foresee this error, better add it explicitely
                raise

    class WindowsLock(object):
        """
        Creates a lock based on the atomic nature of mkdir on Windows
        system calls.
        """
        LOCKBASE = os.path.join(gettempdir(), "bitmask-lock")

        def __init__(self):
            """
            Initializes the lock.
            Sets the lock name to basename plus the process pid.
            """
            self._fd = None
            pid = os.getpid()
            self.name = "%s-%s" % (self.LOCKBASE, pid)
            self.pid = pid

        def get_lock(self):
            """
            Tries to get a lock, and writes the running pid there if successful
            """
            gotit = self._get_lock()
            return gotit

        def _get_lock(self):
            """
            Tries to write to a file with the current pid as part of the name
            """
            try:
                self._fd = os.makedirs(self.name)
            except OSError as exc:
                # could not create the dir
                if exc.args[0] == 183:
                    logger.debug('cannot create dir')
                    # cannot create dir with existing name
                    return False
                else:
                    raise
            return self._is_one_pidfile()[0]

        def _is_one_pidfile(self):
            """
            Returns True, pid if there is only one pidfile with the expected
            base path

            :rtype: tuple
            """
            pidfiles = glob.glob(self.LOCKBASE + '-*')
            if len(pidfiles) == 1:
                pid = pidfiles[0].split('-')[-1]
                return True, int(pid)
            else:
                return False, None

        def get_pid(self):
            """
            Returns the pid of the locking process.

            :rtype: int
            """
            # XXX assert there is only one?
            _, pid = self._is_one_pidfile()
            return pid

        def get_locking_path(self):
            """
            Returns the pid path of the locking process.

            :rtype: str
            """
            pid = self.get_pid()
            if pid:
                return "%s-%s" % (self.LOCKBASE, pid)

        def release_lock(self, name=None):
            """
            Releases the pidfile dir for this process, by removing it.
            """
            if not name:
                name = self.name
            _release_lock(name)

        @classmethod
        def release_all_locks(self):
            """
            Releases all locks. Used for clean shutdown.
            """
            for lockdir in glob.glob("%s-%s" % (self.LOCKBASE, '*')):
                _release_lock(lockdir)

        @property
        def locked_by_us(self):
            """
            Returns True if the pid in the pidfile
            is ours.

            :rtype: bool
            """
            _, pid = self._is_one_pidfile()
            return pid == self.pid

        def update_ts(self):
            """
            Updates the timestamp of the lock.
            """
            if self.locked_by_us:
                update_modification_ts(self.name)

        def write_port(self, port):
            """
            Writes the port for windows control to the pidfile folder
            Returns True if successful.

            :rtype: bool
            """
            if not self.locked_by_us:
                logger.warning("Tried to write control port to a "
                               "non-unique pidfile folder")
                return False
            port_file = os.path.join(self.name, "port")
            with open(port_file, 'w') as f:
                f.write("%s" % port)
            return True

        def get_control_port(self):
            """
            Reads control port of the main instance from the port file
            in the pidfile dir

            :rtype: int
            """
            pid = self.get_pid()
            port_file = os.path.join(self.LOCKBASE + "-%s" % pid, "port")
            port = None
            try:
                with open(port_file) as f:
                    port_str = f.read()
                    port = int(port_str.strip())
            except IOError as exc:
                if exc.errno == errno.ENOENT:
                    logger.error("Tried to read port from non-existent file")
                else:
                    # we did not know explicitely about this error
                    raise
            return port

    def raise_window_ack():
        """
        This function is called from the windows callback that is registered
        with the raise_window event. It just updates the modification time
        of the lock file so we can signal an ack to the instance that tried
        to raise the window.
        """
        lock = WindowsLock()
        lock.update_ts()


def we_are_the_one_and_only():
    """
    Returns True if we are the only instance running, False otherwise.
    If we came later, send a raise signal to the main instance of the
    application.

    Under windows we are not using flock magic, so we wait during
    RAISE_WINDOW_TIMEOUT time, if not ack is
    received, we assume it was a stalled lock, so we remove it and continue
    with initialization.

    :rtype: bool
    """
    _sys = platform.system()

    if _sys in ("Linux", "Darwin"):
        locker = UnixLock('/tmp/bitmask.lock')
        locker.get_lock()
        we_are_the_one = locker.locked_by_us
        if not we_are_the_one:
            signal_event(proto.RAISE_WINDOW)
        return we_are_the_one

    elif _sys == "Windows":
        locker = WindowsLock()
        locker.get_lock()
        we_are_the_one = locker.locked_by_us

        if not we_are_the_one:
            locker.release_lock()
        lock_path = locker.get_locking_path()
        ts = get_modification_ts(lock_path)

        nowfun = datetime.datetime.now
        t0 = nowfun()
        pause = RAISE_WINDOW_TIMEOUT / float(RAISE_WINDOW_WAIT_STEPS)
        timeout_delta = datetime.timedelta(0, RAISE_WINDOW_TIMEOUT)
        check_interval = lambda: nowfun() - t0 < timeout_delta

        # let's assume it's a stalled lock
        we_are_the_one = True
        signal_event(proto.RAISE_WINDOW)

        while check_interval():
            if get_modification_ts(lock_path) > ts:
                # yay! someone claimed their control over the lock.
                # so the lock is alive
                logger.debug('Raise window ACK-ed')
                we_are_the_one = False
                break
            else:
                time.sleep(pause)

        if we_are_the_one:
            # ok, it really was a stalled lock. let's remove all
            # that is left, and put only ours there.
            WindowsLock.release_all_locks()
            WindowsLock().get_lock()

        return we_are_the_one

    else:
        logger.warning("Multi-instance checker "
                       "not implemented for %s" % (_sys))
        # lies, lies, lies...
        return True
