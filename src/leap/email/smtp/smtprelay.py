import re
import gnupg
from zope.interface import implements
from StringIO import StringIO
from twisted.mail import smtp
from twisted.internet.protocol import ServerFactory
from twisted.internet import reactor
from twisted.internet import defer
from twisted.application import internet, service
from twisted.python import log
from email.Header import Header


class SMTPFactory(ServerFactory):
    """
    Factory for an SMTP server with encrypted relaying capabilities.
    """

    def __init__(self, gpg=None):
        self._gpg = gpg

    def buildProtocol(self, addr):
        "Return a protocol suitable for the job."
        # TODO: use ESMTP here.
        smtpProtocol = smtp.SMTP(SMTPDelivery(self._gpg))
        smtpProtocol.factory = self
        return smtpProtocol


class SMTPDelivery(object):
    """
    Validate email addresses and handle message delivery.
    """

    implements(smtp.IMessageDelivery)

    def __init__(self, gpg=None):
        if gpg:
            self._gpg = gpg
        else:
            self._gpg = GPGWrapper()

    def receivedHeader(self, helo, origin, recipients):
        myHostname, clientIP = helo
        headerValue = "by %s from %s with ESMTP ; %s" % (
            myHostname, clientIP, smtp.rfc822date())
        # email.Header.Header used for automatic wrapping of long lines
        return "Received: %s" % Header(headerValue)

    def validateTo(self, user):
        """Assert existence of and trust on recipient's GPG public key."""
        # try to find recipient's public key
        try:
            # this will raise an exception if key is not found
            trust = self._gpg.find_key(user.dest.addrstr)['trust']
            # if key is not ultimatelly trusted, then the message will not
            # be encrypted. So, we check for this below
            #if trust != 'u':
            #    raise smtp.SMTPBadRcpt(user)
            log.msg("Accepting mail for %s..." % user.dest)
            return lambda: EncryptedMessage(user, gpg=self._gpg)
        except LookupError:
            raise smtp.SMTPBadRcpt(user)

    def validateFrom(self, helo, originAddress):
        # accept mail from anywhere. To reject an address, raise
        # smtp.SMTPBadSender here.
        return originAddress


class EncryptedMessage():
    """
    Receive plaintext from client, encrypt it and send message to a
    recipient.
    """
    implements(smtp.IMessage)

    SMTP_HOSTNAME = "mail.riseup.net"
    SMTP_PORT = 25

    def __init__(self, user, gpg=None):
        self.user = user
        self.getSMTPInfo()
        self.lines = []
        if gpg:
            self._gpg = gpg
        else:
            self._gpg = GPGWrapper()

    def lineReceived(self, line):
        """Store email DATA lines as they arrive."""
        self.lines.append(line)

    def eomReceived(self):
        """Encrypt and send message."""
        log.msg("Message data complete.")
        self.lines.append('')  # add a trailing newline
        self.parseMessage()
        try:
            self.encrypt()
            return self.sendMessage()
        except LookupError:
            return None

    def parseMessage(self):
        """Separate message headers from body."""
        sep = self.lines.index('')
        self.headers = self.lines[:sep]
        self.body = self.lines[sep + 1:]

    def connectionLost(self):
        log.msg("Connection lost unexpectedly!")
        log.err()
        # unexpected loss of connection; don't save
        self.lines = []

    def sendSuccess(self, r):
        log.msg(r)

    def sendError(self, e):
        log.msg(e)
        log.err()

    def prepareHeader(self):
        self.headers.insert(1, "From: %s" % self.user.orig.addrstr)
        self.headers.insert(2, "To: %s" % self.user.dest.addrstr)
        self.headers.append('')

    def sendMessage(self):
        self.prepareHeader()
        msg = '\n'.join(self.headers + [self.cyphertext])
        d = defer.Deferred()
        factory = smtp.ESMTPSenderFactory(self.smtp_username,
                                          self.smtp_password,
                                          self.smtp_username,
                                          self.user.dest.addrstr,
                                          StringIO(msg),
                                          d)
        # the next call is TSL-powered!
        reactor.connectTCP(self.SMTP_HOSTNAME, self.SMTP_PORT, factory)
        d.addCallback(self.sendSuccess)
        d.addErrback(self.sendError)
        return d

    def encrypt(self, always_trust=True):
        # TODO: do not "always trust" here.
        fp = self._gpg.find_key(self.user.dest.addrstr)['fingerprint']
        log.msg("Encrypting to %s" % fp)
        self.cyphertext = str(self._gpg.encrypt('\n'.join(self.body), [fp],
                                                always_trust=always_trust))

    # this will be replaced by some other mechanism of obtaining credentials
    # for SMTP server.
    def getSMTPInfo(self):
        #f = open('/media/smtp-info.txt', 'r')
        #self.smtp_host = f.readline().rstrip()
        #self.smtp_port = f.readline().rstrip()
        #self.smtp_username = f.readline().rstrip()
        #self.smtp_password = f.readline().rstrip()
        #f.close()
        self.smtp_host = ''
        self.smtp_port = ''
        self.smtp_username = ''
        self.smtp_password = ''


class GPGWrapper():
    """
    This is a temporary class for handling GPG requests, and should be
    replaced by a more general class used throughout the project.
    """

    GNUPG_HOME = "~/.config/leap/gnupg"
    GNUPG_BINARY = "/usr/bin/gpg"  # TODO: change this based on OS

    def __init__(self, gpghome=GNUPG_HOME, gpgbinary=GNUPG_BINARY):
        self.gpg = gnupg.GPG(gnupghome=gpghome, gpgbinary=gpgbinary)

    def find_key(self, email):
        """
        Find user's key based on their email.
        """
        for key in self.gpg.list_keys():
            for uid in key['uids']:
                if re.search(email, uid):
                    return key
        raise LookupError("GnuPG public key for %s not found!" % email)

    def encrypt(self, data, recipient, always_trust=True):
        # TODO: do not 'always_trust'.
        return self.gpg.encrypt(data, recipient, always_trust=always_trust)

    def decrypt(self, data):
        return self.gpg.decrypt(data)

    def import_keys(self, data):
        return self.gpg.import_keys(data)


# service configuration
port = 25
factory = SMTPFactory()

# these enable the use of this service with twistd
application = service.Application("LEAP SMTP Relay")
service = internet.TCPServer(port, factory)
service.setServiceParent(application)
