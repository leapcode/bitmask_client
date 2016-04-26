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

import os
from distutils.spawn import find_executable


def discover_gpg_binary():
    path = find_executable('gpg')
    if path is None:
        raise Exception('Did not find a gpg executable!')

    if os.path.islink(path):
        path = os.path.realpath(path)

    return path


SYSTEM_CA_BUNDLE = True


class LeapConfig(object):

    def __init__(self,
                 leap_home=None,
                 timeout_in_s=15,
                 start_background_jobs=False,
                 gpg_binary=discover_gpg_binary()):

        self.leap_home = leap_home
        self.timeout_in_s = timeout_in_s
        self.start_background_jobs = start_background_jobs
        self.gpg_binary = gpg_binary
