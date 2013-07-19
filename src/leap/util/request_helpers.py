# -*- coding: utf-8 -*-
# request_helpers.py
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
Request helpers for backward compatible "parsing" of requests
"""

import time

import json

from dateutil import parser as dateparser


def get_content(request):
    """
    Returns the content by trying to get it from the json
    property/function or from content, in that order.
    Also returns the mtime for that content if available

    :param request: request as it is given by requests
    :type request: Response

    :rtype: tuple (contents, mtime)
    """

    contents = ""
    mtime = None

    if request and request.content and request.json:
        if callable(request.json):
            contents = json.dumps(request.json())
        else:
            contents = json.dumps(request.json)
    else:
        contents = request.content

    mtime = None
    last_modified = request.headers.get('last-modified', None)
    if last_modified:
        dt = dateparser.parse(unicode(last_modified))
        mtime = int(time.mktime(dt.timetuple()) + dt.microsecond / 1000000.0)

    return contents, mtime
