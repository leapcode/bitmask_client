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
from StringIO import StringIO
from email.utils import parseaddr
from leap.mail.outgoing.service import OutgoingMail

from twisted.internet.defer import Deferred, fail
from twisted.mail.smtp import SMTPSenderFactory
from twisted.internet import reactor, defer
from pixelated.support.functional import flatten
from twisted.mail.smtp import User


class SMTPDownException(Exception):

    def __init__(self):
        Exception.__init__(self, "Couldn't send mail now, try again later.")


NOT_NEEDED = None


class MailSenderException(Exception):

    def __init__(self, message, email_error_map):
        super(MailSenderException, self).__init__(message, email_error_map)
        self.email_error_map = email_error_map


class MailSender(object):

    def __init__(self, smtp_config, keymanager):
        self._smtp_config = smtp_config
        self._keymanager = keymanager

    @defer.inlineCallbacks
    def sendmail(self, mail):
        recipients = flatten([mail.to, mail.cc, mail.bcc])

        results = yield self._send_mail_to_all_recipients(mail, recipients)
        all_succeeded = reduce(lambda a, b: a and b, [r[0] for r in results])

        if not all_succeeded:
            error_map = self._build_error_map(recipients, results)
            raise MailSenderException(
                'Failed to send mail to all recipients', error_map)

        defer.returnValue(all_succeeded)

    def _send_mail_to_all_recipients(self, mail, recipients):
        outgoing_mail = self._create_outgoing_mail()
        bccs = mail.bcc
        deferreds = []

        for recipient in recipients:
            self._define_bcc_field(mail, recipient, bccs)
            smtp_recipient = self._create_twisted_smtp_recipient(recipient)
            deferreds.append(outgoing_mail.send_message(
                mail.to_smtp_format(), smtp_recipient))

        return defer.DeferredList(deferreds, fireOnOneErrback=False, consumeErrors=True)

    def _define_bcc_field(self, mail, recipient, bccs):
        if recipient in bccs:
            mail.headers['Bcc'] = [recipient]
        else:
            mail.headers['Bcc'] = []

    def _build_error_map(self, recipients, results):
        error_map = {}
        for email, error in [(recipients[idx], r[1]) for idx, r in enumerate(results)]:
            error_map[email] = error
        return error_map

    def _create_outgoing_mail(self):
        return OutgoingMail(str(self._smtp_config.account_email),
                            self._keymanager,
                            self._smtp_config.cert_path,
                            self._smtp_config.cert_path,
                            str(self._smtp_config.remote_smtp_host),
                            int(self._smtp_config.remote_smtp_port))

    def _create_twisted_smtp_recipient(self, recipient):
        # TODO: Better is fix Twisted instead
        recipient = self._remove_canonical_recipient(recipient)
        return User(str(recipient), NOT_NEEDED, NOT_NEEDED, NOT_NEEDED)

    def _remove_canonical_recipient(self, recipient):
        return recipient.split('<')[1][0:-1] if '<' in recipient else recipient
