from datetime import datetime
import re
from leap.email.smtp.smtprelay import (
    SMTPFactory,   # a ServerFactory
    #SMTPDelivery, # an object
    #EncryptedMessage,
)
from leap.email.smtp import tests
from twisted.internet.error import ConnectionDone
from twisted.test import proto_helpers


class TestSmtpRelay(tests.OpenPGPTestCase):
    
    IP_REGEX = "(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])";
    HOSTNAME_REGEX = "(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])";
    IP_OR_HOST_REGEX = '(' + IP_REGEX + '|' + HOSTNAME_REGEX + ')'
    
    CRLF = '\r\n'
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
    SMTP_ANSWERS = [ '220 ' + IP_OR_HOST_REGEX + ' NO UCE NO UBE NO RELAY PROBES',
                     '250 ' + IP_OR_HOST_REGEX + ' Hello ' + IP_OR_HOST_REGEX + ', nice to meet you',
                     '250 Sender address accepted',
                     '250 Recipient address accepted',
                     '354 Continue' ]
    

    def setUp(self):
        super(TestSmtpRelay, self).setUp()
        self.proto = SMTPFactory(self._gpg).buildProtocol(('127.0.0.1',0))
        self.transport = proto_helpers.StringTransport()
        self.proto.makeConnection(self.transport)


    def tearDown(self):
        self.proto.setTimeout(None)
        super(TestSmtpRelay, self).tearDown()

    
    def assertMatch(self, string, pattern, msg=None):
        if not re.match(pattern, string):
            msg = self._formatMessage(msg, '"%s" does not match pattern "%s".'
            % (string, pattern))
            raise self.failureException(msg)


    def test_send_email(self):
        """
        If L{smtp.SMTP} receives an empty line, it responds with a 500 error
        response code and a message about a syntax error.
        """
        for i, line in enumerate(self.EMAIL_DATA):
            self.proto.lineReceived(line+self.CRLF)
            self.assertMatch(self.transport.value(),
                             self.CRLF.join(self.SMTP_ANSWERS[0:i+1]))

