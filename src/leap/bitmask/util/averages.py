# -*- coding: utf-8 -*-
# averages.py
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
Utility class for moving averages.

It is used in the status panel widget for displaying up and down
download rates.
"""
from leap.bitmask.util import first


class RateMovingAverage(object):
    """
    Moving window average for calculating
    upload and download rates.
    """
    SAMPLE_SIZE = 5

    def __init__(self):
        """
        Initializes an empty array of fixed size
        """
        self.reset()

    def reset(self):
        self._data = [None for i in xrange(self.SAMPLE_SIZE)]

    def append(self, x):
        """
        Appends a new data point to the collection.

        :param x: A tuple containing timestamp and traffic points
                  in the form (timestamp, traffic)
        :type x: tuple
        """
        self._data.pop(0)
        self._data.append(x)

    def get(self):
        """
        Gets the collection.
        """
        return self._data

    def get_average(self):
        """
        Gets the moving average.
        """
        data = filter(None, self.get())
        traff = [traffic for (ts, traffic) in data]
        times = [ts for (ts, traffic) in data]

        try:
            deltatraffic = traff[-1] - first(traff)
            deltat = (times[-1] - first(times)).seconds
        except IndexError:
            deltatraffic = 0
            deltat = 0

        try:
            rate = float(deltatraffic) / float(deltat) / 1024
        except ZeroDivisionError:
            rate = 0

        # In some cases we get negative rates
        if rate < 0:
            rate = 0

        return rate

    def get_total(self):
        """
        Gets the total accumulated throughput.
        """
        try:
            return self._data[-1][1] / 1024
        except TypeError:
            return 0
