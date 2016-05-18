# -*- coding: utf-8 -*-
# api.py
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
Registry for the public API for the Bitmask Backend.
"""
from collections import OrderedDict

registry = OrderedDict()


class APICommand(type):
    """
    A metaclass to keep a global registry of all the methods that compose the
    public API for the Bitmask Backend.
    """
    def __init__(cls, name, bases, attrs):
        for key, val in attrs.iteritems():
            properties = getattr(val, 'register', None)
            label = getattr(cls, 'label', None)
            if label:
                name = label
            if properties is not None:
                registry['%s.%s' % (name, key)] = properties


def register_method(*args):
    """
    This method gathers info about all the methods that are supposed to
    compose the public API to communicate with the backend.

    It sets up a register property for any method that uses it.
    A type annotation is supposed to be in this property.
    The APICommand metaclass collects these properties of the methods and
    stores them in the global api_registry object, where they can be
    introspected at runtime.
    """
    def decorator(f):
        f.register = tuple(args)
        return f
    return decorator
