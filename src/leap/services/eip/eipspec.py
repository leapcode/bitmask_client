# -*- coding: utf-8 -*-
# eipspec.py
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


# Schemas dict
# To add a schema for a version you should follow the form:
# { '1': schema_v1, '2': schema_v2, ... etc }
# so for instance, to add the '2' version, you should do:
# eipservice_config_spec['2'] = schema_v2
eipservice_config_spec = {}

eipservice_config_spec['1'] = {
    'description': 'sample eip service config',
    'type': 'object',
    'properties': {
        'serial': {
            'type': int,
            'default': 1,
            'required': ["True"]
        },
        'version': {
            'type': int,
            'default': 1,
            'required': ["True"]
        },
        'clusters': {
            'type': list,
            'default': [
                {"label": {
                    "en": "Location Unknown"},
                    "name": "location_unknown"}]
        },
        'gateways': {
            'type': list,
            'default': [
                {"capabilities": {
                    "adblock": True,
                    "filter_dns": True,
                    "ports": ["80", "53", "443", "1194"],
                    "protocols": ["udp", "tcp"],
                    "transport": ["openvpn"],
                    "user_ips": False},
                 "cluster": "location_unknown",
                 "host": "location.example.org",
                 "ip_address": "127.0.0.1"}]
        },
        'locations': {
            'type': dict,
            'default': {}
        },
        'openvpn_configuration': {
            'type': dict,
            'default': {
                "auth": None,
                "cipher": None,
                "tls-cipher": None}
        }
    }
}


def get_schema(version):
    """
    Returns the schema corresponding to the version given.

    :param version: the version of the schema to get.
    :type version: str
    :rtype: dict or None if the version is not supported.
    """
    schema = eipservice_config_spec.get(version, None)
    return schema
