from zope.interface import implements
from twisted.mail import smtp
from twisted.internet.protocol import ServerFactory
from twisted.internet import reactor
from twisted.internet import defer
from email.Header import Header
from StringIO import StringIO


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
    
    def __init__(self):
        self.gpgkey = ''

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
        return lambda: EncryptedMessage(user, self.gpgkey)

    def validateFrom(self, helo, originAddress):
        # accept mail from anywhere. To reject an address, raise
        # smtp.SMTPBadSender here.
        return originAddress


class EncryptedMessage():
    """
    Receive plaintext from client, encrypt it and send message to
    recipients.
    """
    implements(smtp.IMessage)

    SMTP_HOSTNAME = "mail.riseup.net"
    SMTP_PORT     = 25

    def __init__(self, user, gpgkey):
        self.user = user
        self.gpgkey = gpgkey
        self.getSMTPInfo()
        self.lines = []

    def lineReceived(self, line):
        """Store email DATA lines as they arrive."""
        self.lines.append(line)

    def eomReceived(self):
        """Encrypt and send message."""
        print "Message data complete."
        self.lines.append('') # add a trailing newline
        return self.sendMail()

    def connectionLost(self):
        print "Connection lost unexpectedly!"
        # unexpected loss of connection; don't save
        del(self.lines)

    def sendSuccess(self, r):
        print r
        reactor.stop()

    def sendError(self, e):
        print e
        reactor.stop()

    def sendMail(self):
        self.lines = [self.lines[0]] + \
                     ["From: %s" % self.user.orig.addrstr] + \
                     ["To: %s" % self.user.dest.addrstr] + \
                     self.lines[1:]
        msg = '\n'.join(self.lines)
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
        #reactor.run()
        return d

    
    # this will be replaced by some other mechanism of obtaining credentials
    # for SMTP server.
    def getSMTPInfo(self):
        f = open('/var/tmp/smtp-info.txt', 'r')
        self.smtp_host = f.readline().rstrip()
        self.smtp_port = f.readline().rstrip()
        self.smtp_username = f.readline().rstrip()
        self.smtp_password = f.readline().rstrip()
        f.close()


# run server
if __name__ == "__main__":
    import sys
    reactor.listenTCP(25, SMTPFactory())
    reactor.run()
