# -*- coding: utf-8 -*-
# api_contract.py
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
Display a human-readable representation of the methods that compound the public
api for Bitmask Core.

The values are meant to be type annotations.
"""

if __name__ == "__main__":
    from leap.bitmask.core.service import BitmaskBackend
    from leap.bitmask.core import api
    backend = BitmaskBackend()

    print '========= Bitmask Core API =================='
    print

    for key in api.registry:
        human_key = key.replace('do_', '').lower()
        value = api.registry[key]

        print("{}:\t\t{}".format(
            human_key,
            ' '.join([x for x in value])))
    print
    print '============================================='
