# -*- coding: utf-8 -*-
# smtpspec.py
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

smtp_config_spec = {
    'description': 'sample smtp service config',
    'type': 'object',
    'properties': {
        'serial': {
            'type': int,
            'default': 1,
            'required': True
        },
        'version': {
            'type': int,
            'default': 1,
            'required': True
        },
        'hosts': {
            'type': dict,
            'default': {
                "walrus": {
                    "hostname": "someprovider",
                    "ip_address": "1.1.1.1",
                    "port": 1111
                },
            },
        },
        'locations': {
            'type': dict,
            'default': {
                "locations": {

                }
            }
        }
    }
}
