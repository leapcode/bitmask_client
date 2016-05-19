# -*- coding: utf-8 -*-
# dummy.py
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
An authoritative dummy backend for tests.
"""
import json

from leap.common.service_hooks import HookableService


class BackendCommands(object):

    """
    General commands for the BitmaskBackend Core Service.
    """

    def __init__(self, core):
        self.core = core

    def do_status(self):
        return json.dumps(
            {'soledad': 'running',
             'keymanager': 'running',
             'mail': 'running',
             'eip': 'stopped',
             'backend': 'dummy'})

    def do_version(self):
        return {'version_core': '0.0.1'}

    def do_stats(self):
        return {'mem_usage': '01 KB'}

    def do_shutdown(self):
        return {'shutdown': 'ok'}


class mail_services(object):

    class SoledadService(HookableService):
        pass

    class KeymanagerService(HookableService):
        pass

    class StandardMailService(HookableService):
        pass


class BonafideService(HookableService):

    def __init__(self, basedir):
        pass

    def do_authenticate(self, user, password):
        return {u'srp_token': u'deadbeef123456789012345678901234567890123',
                u'uuid': u'01234567890abcde01234567890abcde'}

    def do_signup(self, user, password):
        return {'signup': 'ok', 'user': 'dummyuser@provider.example.org'}

    def do_logout(self, user):
        return {'logout': 'ok'}

    def do_get_active_user(self):
        return 'dummyuser@provider.example.org'
