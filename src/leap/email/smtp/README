Leap SMTP Relay
===============

Outgoing mail workflow:

    * LEAP client runs a thin SMTP proxy on the user's device, bound to
      localhost.
    * User's MUA is configured outgoing SMTP to localhost
    * When SMTP proxy receives an email from MUA
        * SMTP proxy queries Key Manager for the user's private key and public
          keys of all recipients
        * Message is signed by sender and encrypted to recipients.
        * If recipient's key is missing, email goes out in cleartext (unless
          user has configured option to send only encrypted email)
        * Finally, message is relayed to provider's SMTP relay


Dependencies
------------

Leap SMTP Relay depends on the following python libraries:

  * Twisted 12.3.0 [1]
  * zope.interface 4.0.3 [2]

[1] http://pypi.python.org/pypi/Twisted/12.3.0
[2] http://pypi.python.org/pypi/zope.interface/4.0.3


How to run
----------

To launch the SMTP relay, run the following command:

  twistd -y smtprelay.tac


Running tests
-------------

Tests are run using Twisted's Trial API, like this:

  trial leap.email.smtp.tests
