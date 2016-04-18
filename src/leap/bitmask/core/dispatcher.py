# -*- coding: utf-8 -*-
# dispatcher.py
# Copyright (C) 2016 LEAP
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
Command dispatcher.
"""
import json

from twisted.internet import defer
from twisted.python import failure, log


# TODO implement sub-classes to dispatch subcommands (user, mail).


class CommandDispatcher(object):

    def __init__(self, core):

        self.core = core

    def _get_service(self, name):

        try:
            return self.core.getServiceNamed(name)
        except KeyError:
            return None

    def dispatch(self, msg):
        cmd = msg[0]

        _method = getattr(self, 'do_' + cmd.upper(), None)

        if not _method:
            return defer.fail(failure.Failure(RuntimeError('No such command')))

        return defer.maybeDeferred(_method, *msg)

    def do_STATS(self, *parts):
        return _format_result(self.core.do_stats())

    def do_VERSION(self, *parts):
        return _format_result(self.core.do_version())

    def do_STATUS(self, *parts):
        return _format_result(self.core.do_status())

    def do_SHUTDOWN(self, *parts):
        return _format_result(self.core.do_shutdown())

    def do_USER(self, *parts):

        subcmd = parts[1]
        user, password = parts[2], parts[3]

        bf = self._get_service('bonafide')

        if subcmd == 'authenticate':
            d = bf.do_authenticate(user, password)

        elif subcmd == 'signup':
            d = bf.do_signup(user, password)

        elif subcmd == 'logout':
            d = bf.do_logout(user, password)

        elif subcmd == 'active':
            d = bf.do_get_active_user()

        d.addCallbacks(_format_result, _format_error)
        return d

    def do_EIP(self, *parts):

        subcmd = parts[1]
        eip_label = 'eip'

        if subcmd == 'enable':
            return _format_result(
                self.core.do_enable_service(eip_label))

        eip = self._get_service(eip_label)
        if not eip:
            return _format_result('eip: disabled')

        if subcmd == 'status':
            return _format_result(eip.do_status())

        elif subcmd == 'disable':
            return _format_result(
                self.core.do_disable_service(eip_label))

        elif subcmd == 'start':
            # TODO --- attempt to get active provider
            # TODO or catch the exception and send error
            provider = parts[2]
            d = eip.do_start(provider)
            d.addCallbacks(_format_result, _format_error)
            return d

        elif subcmd == 'stop':
            d = eip.do_stop()
            d.addCallbacks(_format_result, _format_error)
            return d

    def do_MAIL(self, *parts):

        subcmd = parts[1]
        mail_label = 'mail'

        if subcmd == 'enable':
            return _format_result(
                self.core.do_enable_service(mail_label))

        m = self._get_service(mail_label)
        bf = self._get_service('bonafide')

        if not m:
            return _format_result('mail: disabled')

        if subcmd == 'status':
            return _format_result(m.do_status())

        elif subcmd == 'disable':
            return _format_result(self.core.do_disable_service(mail_label))

        elif subcmd == 'get_imap_token':
            d = m.get_imap_token()
            d.addCallbacks(_format_result, _format_error)
            return d

        elif subcmd == 'get_smtp_token':
            d = m.get_smtp_token()
            d.addCallbacks(_format_result, _format_error)
            return d

        elif subcmd == 'get_smtp_certificate':
            # TODO move to mail service
            # TODO should ask for confirmation? like --force or something,
            # if we already have a valid one. or better just refuse if cert
            # exists.
            # TODO how should we pass the userid??
            # - Keep an 'active' user in bonafide (last authenticated)
            # (doing it now)
            # - Get active user from Mail Service (maybe preferred?)
            # - Have a command/method to set 'active' user.

            @defer.inlineCallbacks
            def save_cert(cert_data):
                userid, cert_str = cert_data
                cert_path = yield m.do_get_smtp_cert_path(userid)
                with open(cert_path, 'w') as outf:
                    outf.write(cert_str)
                defer.returnValue('certificate saved to %s' % cert_path)

            d = bf.do_get_smtp_cert()
            d.addCallback(save_cert)
            d.addCallbacks(_format_result, _format_error)
            return d

    def do_KEYS(self, *parts):
        subcmd = parts[1]

        keymanager_label = 'keymanager'
        km = self._get_service(keymanager_label)
        bf = self._get_service('bonafide')

        if not km:
            return _format_result('keymanager: disabled')

        if subcmd == 'list_keys':
            d = bf.do_get_active_user()
            d.addCallback(km.do_list_keys)
            d.addCallbacks(_format_result, _format_error)
            return d


def _format_result(result):
    return json.dumps({'error': None, 'result': result})


def _format_error(failure):
    log.err(failure)
    return json.dumps({'error': failure.value.message, 'result': None})
