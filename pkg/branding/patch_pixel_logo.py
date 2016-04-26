# -*- coding: utf-8 -*-
# patch_pixelated_logo.py
# Copyright (C) 2016 LEAP Encryption Acess Project
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
Patch the Pixelated Logo in the index.html, replacing it with a rebranded
Bitmask Logo. To be used in the pixelated_www assets distributed with the
Bitmask bundles.
"""
__author__ = 'Kali Kaneko <kali@leap.se>'

import os
import sys

from BeautifulSoup import BeautifulSoup


def patch_logo(orig_path, replacement_path):

    with open(orig_path, 'r') as of:
        orig = BeautifulSoup(of.read())

    with open(replacement_path, 'r') as rf:
        new = BeautifulSoup(rf.read())

    new_svg = new.find('svg')
    old_svg = orig.find('svg')
    old_svg.replaceWith(new_svg)

    with open(orig_path, 'w') as f:
        f.write(str(orig))


if __name__ == "__main__":
    here = os.path.dirname(os.path.realpath(__file__))
    if len(sys.argv) > 1:
        orig_path = sys.argv[1]
    else:
        import pixelated_www
        orig_path = os.path.join(pixelated_www.__path__[0],
                                 'index.html')
    assert os.path.isfile(orig_path)
    new_path = os.path.join(here, 'bitmask-logo.svg')
    print('>>> patching file %s with logo in %s' % (orig_path, new_path))
    patch_logo(orig_path, new_path)
