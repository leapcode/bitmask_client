# License?

"""A U1DB implementation that uses OpenStack Swift as its persistence layer."""

from leap import *
from openstack import *

import gnupg

class GPGWrapper():
    """
    This is a temporary class for handling GPG requests, and should be
    replaced by a more general class used throughout the project.
    """

    GNUPG_HOME    = "~/.config/leap/gnupg"
    GNUPG_BINARY  = "/usr/bin/gpg" # this has to be changed based on OS

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

    def encrypt(self, data, recipient, sign=None, always_trust=False,
                passphrase=None, symmetric=False):
        return self.gpg.encrypt(data, recipient, sign=sign,
                                always_trust=always_trust,
                                passphrase=passphrase, symmetric=symmetric)

    def decrypt(self, data, always_trust=False, passphrase=None):
        return self.gpg.decrypt(data, always_trust=always_trust,
                                passphrase=passphrase)

    def import_keys(self, data):
        return self.gpg.import_keys(data)
