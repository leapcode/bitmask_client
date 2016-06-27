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

from .api import APICommand, register_method


class SubCommand(object):

    __metaclass__ = APICommand

    def dispatch(self, service, *parts, **kw):
        subcmd = parts[1]

        _method = getattr(self, 'do_' + subcmd.upper(), None)
        if not _method:
            raise RuntimeError('No such subcommand')
        return _method(service, *parts, **kw)


class UserCmd(SubCommand):

    label = 'user'

    @register_method("{'srp_token': unicode, 'uuid': unicode}")
    def do_AUTHENTICATE(self, bonafide, *parts):
        user, password = parts[2], parts[3]
        d = defer.maybeDeferred(bonafide.do_authenticate, user, password)
        return d

    @register_method("{'signup': 'ok', 'user': str}")
    def do_SIGNUP(self, bonafide, *parts):
        user, password = parts[2], parts[3]
        d = defer.maybeDeferred(bonafide.do_signup, user, password)
        return d

    @register_method("{'logout': 'ok'}")
    def do_LOGOUT(self, bonafide, *parts):
        user = parts[2]
        d = defer.maybeDeferred(bonafide.do_logout, user)
        return d

    @register_method('str')
    def do_ACTIVE(self, bonafide, *parts):
        d = defer.maybeDeferred(bonafide.do_get_active_user)
        return d


class EIPCmd(SubCommand):

    label = 'eip'

    @register_method('dict')
    def do_ENABLE(self, service, *parts):
        d = service.do_enable_service(self.label)
        return d

    @register_method('dict')
    def do_DISABLE(self, service, *parts):
        d = service.do_disable_service(self.label)
        return d

    @register_method('dict')
    def do_STATUS(self, eip, *parts):
        d = eip.do_status()
        return d

    @register_method('dict')
    def do_START(self, eip, *parts):
        # TODO --- attempt to get active provider
        # TODO or catch the exception and send error
        provider = parts[2]
        d = eip.do_start(provider)
        return d

    @register_method('dict')
    def do_STOP(self, eip, *parts):
        d = eip.do_stop()
        return d


class MailCmd(SubCommand):

    label = 'mail'

    @register_method('dict')
    def do_ENABLE(self, service, *parts, **kw):
        d = service.do_enable_service(self.label)
        return d

    @register_method('dict')
    def do_DISABLE(self, service, *parts, **kw):
        d = service.do_disable_service(self.label)
        return d

    @register_method('dict')
    def do_STATUS(self, mail, *parts, **kw):
        d = mail.do_status()
        return d

    @register_method('dict')
    def do_GET_TOKEN(self, mail, *parts, **kw):
        d = mail.get_token()
        return d

    @register_method('dict')
    def do_GET_SMTP_CERTIFICATE(self, mail, *parts, **kw):
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
            cert_path = yield mail.do_get_smtp_cert_path(userid)
            with open(cert_path, 'w') as outf:
                outf.write(cert_str)
            defer.returnValue('certificate saved to %s' % cert_path)

        bonafide = kw['bonafide']
        d = bonafide.do_get_smtp_cert()
        d.addCallback(save_cert)
        return d


class KeysCmd(SubCommand):

    label = 'keys'

    @register_method("[[str, str]]")
    def do_LIST(self, service, *parts, **kw):
        bonafide = kw['bonafide']
        d = bonafide.do_get_active_user()
        d.addCallback(service.do_list_keys)
        return d

    @register_method('str')
    def do_EXPORT(self, service, *parts, **kw):
        # TODO
        return defer.succeed("")


class CommandDispatcher(object):

    __metaclass__ = APICommand

    label = 'core'

    def __init__(self, core):

        self.core = core
        self.subcommand_user = UserCmd()
        self.subcommand_eip = EIPCmd()
        self.subcommand_mail = MailCmd()
        self.subcommand_keys = KeysCmd()

    # XXX --------------------------------------------
    # TODO move general services to another subclass

    @register_method("{'mem_usage': str}")
    def do_STATS(self, *parts):
        return _format_result(self.core.do_stats())

    @register_method("{version_core': '0.0.0'}")
    def do_VERSION(self, *parts):
        return _format_result(self.core.do_version())

    @register_method("{'mail': 'running'}")
    def do_STATUS(self, *parts):
        return _format_result(self.core.do_status())

    @register_method("{'shutdown': 'ok'}")
    def do_SHUTDOWN(self, *parts):
        return _format_result(self.core.do_shutdown())

    # -----------------------------------------------

    def do_USER(self, *parts):
        bonafide = self._get_service('bonafide')
        d = self.subcommand_user.dispatch(bonafide, *parts)
        d.addCallbacks(_format_result, _format_error)
        return d

    def do_EIP(self, *parts):
        eip = self._get_service(self.subcommand_eip.label)
        if not eip:
            return _format_result('eip: disabled')
        subcmd = parts[1]

        dispatch = self._subcommand_eip.dispatch
        if subcmd in ('enable', 'disable'):
            d = dispatch(self.core, *parts)
        else:
            d = dispatch(eip, *parts)

        d.addCallbacks(_format_result, _format_error)
        return d

    def do_MAIL(self, *parts):
        subcmd = parts[1]
        dispatch = self.subcommand_mail.dispatch

        if subcmd == 'enable':
            d = dispatch(self.core, *parts)

        mail = self._get_service(self.subcommand_mail.label)
        bonafide = self._get_service('bonafide')
        kw = {'bonafide': bonafide}

        if not mail:
            return _format_result('mail: disabled')

        if subcmd == 'disable':
            d = dispatch(self.core)
        else:
            d = dispatch(mail, *parts, **kw)

        d.addCallbacks(_format_result, _format_error)
        return d

    def do_KEYS(self, *parts):
        dispatch = self.subcommand_keys.dispatch

        keymanager_label = 'keymanager'
        keymanager = self._get_service(keymanager_label)
        bonafide = self._get_service('bonafide')
        kw = {'bonafide': bonafide}

        if not keymanager:
            return _format_result('keymanager: disabled')

        d = dispatch(keymanager, *parts, **kw)
        d.addCallbacks(_format_result, _format_error)
        return d

    def dispatch(self, msg):
        cmd = msg[0]

        _method = getattr(self, 'do_' + cmd.upper(), None)

        if not _method:
            return defer.fail(failure.Failure(RuntimeError('No such command')))

        return defer.maybeDeferred(_method, *msg)

    def _get_service(self, name):
        try:
            return self.core.getServiceNamed(name)
        except KeyError:
            return None


def _format_result(result):
    return json.dumps({'error': None, 'result': result})


def _format_error(failure):
    log.err(failure)
    return json.dumps({'error': failure.value.message, 'result': None})
