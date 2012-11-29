# Copyright 2011 Canonical Ltd.
#
# This file is part of u1db.
#
# u1db is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# u1db is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with u1db.  If not, see <http://www.gnu.org/licenses/>.

import errno
import time


def safe_close(process, timeout=0.1):
    """Shutdown the process in the nicest fashion you can manage.

    :param process: A subprocess.Popen object.
    :param timeout: We'll try to send 'SIGTERM' but if the process is alive
        longer that 'timeout', we'll send SIGKILL.
    """
    if process.poll() is not None:
        return
    try:
        process.terminate()
    except OSError, e:
        if e.errno in (errno.ESRCH,):
            # Process has exited
            return
    tend = time.time() + timeout
    while time.time() < tend:
        if process.poll() is not None:
            return
        time.sleep(0.01)
    try:
        process.kill()
    except OSError, e:
        if e.errno in (errno.ESRCH,):
            # Process has exited
            return
    process.wait()
