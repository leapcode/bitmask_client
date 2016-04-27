#
# Copyright (c) 2014 ThoughtWorks, Inc.
#
# Pixelated is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pixelated is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.
import time
import logging
from functools import wraps
from twisted.internet import defer


log = logging.getLogger(__name__)


def _start_stopwatch():
    return (time.time(), time.clock())


def _stop_stopwatch(start):
    start_time, start_clock = start
    end_clock = time.clock()
    end_time = time.time()
    clock_duration = end_clock - start_clock
    time_duration = end_time - start_time
    if time_duration < 0.00000001:    # avoid division by zero
        time_duration = 0.00000001

    estimate_percent_io = (
        (time_duration - clock_duration) / time_duration) * 100.0

    return time_duration, clock_duration, estimate_percent_io


def log_time(f):

    @wraps(f)
    def wrapper(*args, **kwds):
        start = _start_stopwatch()

        result = f(*args, **kwds)

        time_duration, clock_duration, estimate_percent_io = _stop_stopwatch(
            start)
        log.info('Needed %fs (%fs cpu time, %.2f%% spent outside process) to execute  %s' % (
            time_duration, clock_duration, estimate_percent_io, f))

        return result

    return wrapper


def log_time_deferred(f):

    def log_time(result, start):
        time_duration, clock_duration, estimate_percent_io = _stop_stopwatch(
            start)
        log.info('after callback: Needed %fs (%fs cpu time, %.2f%% spent outside process) to execute  %s' % (
            time_duration, clock_duration, estimate_percent_io, f))
        return result

    @wraps(f)
    def wrapper(*args, **kwds):
        start = _start_stopwatch()
        result = f(*args, **kwds)
        if isinstance(result, defer.Deferred):
            result.addCallback(log_time, start=start)
        else:
            log.warn('No Deferred returned, perhaps need to re-order annotations?')
        return result

    return wrapper
