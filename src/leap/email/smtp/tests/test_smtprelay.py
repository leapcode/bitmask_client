from datetime import datetime
import re
from leap.email.smtp.smtprelay import (
    SMTPFactory,
    #SMTPDelivery, # an object
    EncryptedMessage,
)
from leap.email.smtp import tests
from twisted.internet.error import ConnectionDone
from twisted.test import proto_helpers
from twisted.internet import defer
from twisted.mail.smtp import User


# some regexps
IP_REGEX = "(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])";
HOSTNAME_REGEX = "(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])";
IP_OR_HOST_REGEX = '(' + IP_REGEX + '|' + HOSTNAME_REGEX + ')'

class TestSmtpRelay(tests.OpenPGPTestCase):
    

    EMAIL_DATA = [ 'HELO relay.leap.se',
                   'MAIL FROM: <user@leap.se>',
                   'RCPT TO: <leap@leap.se>',
                   'DATA',
                   'From: User <user@leap.se>',
                   'To: Leap <leap@leap.se>',
                   'Date: ' + datetime.now().strftime('%c'),
                   'Subject: test message',
                   '',
                   'This is a secret message.',
                   'Yours,',
                   'A.',
                   '',
                   '.',
                   'QUIT' ]


    def assertMatch(self, string, pattern, msg=None):
        if not re.match(pattern, string):
            msg = self._formatMessage(msg, '"%s" does not match pattern "%s".'
            % (string, pattern))
            raise self.failureException(msg)


    def test_relay_accepts_valid_email(self):
        """
        Test if SMTP server responds correctly for valid interaction.
        """
        SMTP_ANSWERS = [ '220 ' + IP_OR_HOST_REGEX + ' NO UCE NO UBE NO RELAY PROBES',
                         '250 ' + IP_OR_HOST_REGEX + ' Hello ' + IP_OR_HOST_REGEX + ', nice to meet you',
                         '250 Sender address accepted',
                         '250 Recipient address accepted',
                         '354 Continue' ]
        proto = SMTPFactory(self._gpg).buildProtocol(('127.0.0.1',0))
        transport = proto_helpers.StringTransport()
        proto.makeConnection(transport)
        for i, line in enumerate(self.EMAIL_DATA):
            proto.lineReceived(line + '\r\n')
            self.assertMatch(transport.value(),
                             '\r\n'.join(SMTP_ANSWERS[0:i+1]))
        proto.setTimeout(None)


    def test_message_encrypt(self):
        proto = SMTPFactory(self._gpg).buildProtocol(('127.0.0.1',0))
        user = User('leap@leap.se', 'relay.leap.se', proto, 'leap@leap.se')
        m = EncryptedMessage(user, self._gpg)
        for line in self.EMAIL_DATA[4:12]:
            m.lineReceived(line)
        m.parseMessage()
        m.encrypt()
        decrypted = str(self._gpg.decrypt(m.cyphertext))
        self.assertEqual('\n'.join(self.EMAIL_DATA[9:12]), decrypted)

