import re
import gnupg
from zope.interface import implements
from StringIO import StringIO
from twisted.mail import smtp
from twisted.internet.protocol import ServerFactory
from twisted.internet import reactor
from twisted.internet import defer
from twisted.application import internet, service
from email.Header import Header


class SMTPFactory(ServerFactory):
    """
    Factory for an SMTP server with encrypted relaying capabilities.
    """

    def buildProtocol(self, addr):
        "Return a protocol suitable for the job."
        smtpProtocol = smtp.SMTP(SMTPDelivery())
        smtpProtocol.factory = self
        return smtpProtocol


class SMTPDelivery(object):
    """
    Validate email addresses and handle message delivery.
    """

    implements(smtp.IMessageDelivery)
    
    def receivedHeader(self, helo, origin, recipients):
        myHostname, clientIP = helo
        headerValue = "by %s from %s with ESMTP ; %s" % (
            myHostname, clientIP, smtp.rfc822date( ))
        # email.Header.Header used for automatic wrapping of long lines
        return "Received: %s" % Header(headerValue)

    def validateTo(self, user):
        """Assert existence of GPG public key for a recipient."""
        # for now just accept any receipient
        print "Accepting mail for %s..." % user.dest
        return lambda: EncryptedMessage(user)

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
    SMTP_PORT     = 25

    def __init__(self, user):
        self.user = user
        self.getSMTPInfo()
        self.lines = []
        self.gpg = GPGWrapper()

    def lineReceived(self, line):
        """Store email DATA lines as they arrive."""
        self.lines.append(line)

    def eomReceived(self):
        """Encrypt and send message."""
        print "Message data complete."
        self.lines.append('') # add a trailing newline
        self.parseMessage()
        self.encrypt()
        return self.sendMessage()

    def parseMessage(self):
        """Separate message headers from body."""
        sep = self.lines.index('')
        self.header = self.lines[:sep]
        self.body = self.lines[sep+1:]

    def connectionLost(self):
        print "Connection lost unexpectedly!"
        # unexpected loss of connection; don't save
        self.lines = []

    def sendSuccess(self, r):
        print r

    def sendError(self, e):
        print e

    def prepareHeader(self):
        self.header.insert(1, "From: %s" % self.user.orig.addrstr)
        self.header.insert(2, "To: %s" % self.user.dest.addrstr)
        self.header.append('')

    def sendMessage(self):
        self.prepareHeader()
        msg = '\n'.join(self.header+[self.cyphertext])
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

    def encrypt(self):
        fp = self.gpg.get_fingerprint(self.user.dest.addrstr)
        print "Encrypting to %s" % fp
        self.cyphertext = str(self.gpg.encrypt('\n'.join(self.body), [fp]))
    
    # this will be replaced by some other mechanism of obtaining credentials
    # for SMTP server.
    def getSMTPInfo(self):
        f = open('/media/smtp-info.txt', 'r')
        self.smtp_host = f.readline().rstrip()
        self.smtp_port = f.readline().rstrip()
        self.smtp_username = f.readline().rstrip()
        self.smtp_password = f.readline().rstrip()
        f.close()


class GPGWrapper():
    """
    This is a temporary class for handling GPG requests, and should be
    replaced by a more general class used throughout the project.
    """

    GNUPG_HOME    = "~/.config/leap/gnupg"
    GNUPG_BINARY  = "/usr/bin/gpg" # this has to be changed based on OS

    def __init__(self):
        self.gpg = gnupg.GPG(gnupghome=self.GNUPG_HOME, gpgbinary=self.GNUPG_BINARY)

    def get_fingerprint(self, email):
        """
        Find user's fingerprint based on their email.
        """
        for key in self.gpg.list_keys():
            for uid in key['uids']:
                if re.search(email, uid):
                    return key['fingerprint']

    def encrypt(self, data, recipient):
        return self.gpg.encrypt(data, recipient)


# service configuration
port = 25
factory = SMTPFactory()

# this enables the use of this application with twistd
application = service.Application("LEAP SMTP Relay")  # create the Application
service = internet.TCPServer(port, factory) # create the service
# add the service to the application
service.setServiceParent(application)
