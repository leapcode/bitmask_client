import os
import gnupg
import re


class GPGWrapper(gnupg.GPG):
    """
    This is a temporary class for handling GPG requests, and should be
    replaced by a more general class used throughout the project.
    """

    GNUPG_HOME = os.environ['HOME'] + "/.config/leap/gnupg"
    GNUPG_BINARY = "/usr/bin/gpg"  # this has to be changed based on OS

    def __init__(self, gpghome=GNUPG_HOME, gpgbinary=GNUPG_BINARY):
        super(GPGWrapper, self).__init__(gnupghome=gpghome,
                                         gpgbinary=gpgbinary)

    def find_key(self, email):
        """
        Find user's key based on their email.
        """
        for key in self.list_keys():
            for uid in key['uids']:
                if re.search(email, uid):
                    return key
        raise LookupError("GnuPG public key for %s not found!" % email)

    def encrypt(self, data, recipient, sign=None, always_trust=True,
                passphrase=None, symmetric=False):
        # TODO: devise a way so we don't need to "always trust".
        return super(GPGWrapper, self).encrypt(data, recipient, sign=sign,
                                               always_trust=always_trust,
                                               passphrase=passphrase,
                                               symmetric=symmetric)

    def decrypt(self, data, always_trust=True, passphrase=None):
        # TODO: devise a way so we don't need to "always trust".
        return super(GPGWrapper, self).decrypt(data,
                                               always_trust=always_trust,
                                               passphrase=passphrase)

    def send_keys(self, keyserver, *keyids):
        """
        Send keys to a keyserver
        """
        result = self.result_map['list'](self)
        logger.debug('send_keys: %r', keyids)
        data = _make_binary_stream("", self.encoding)
        args = ['--keyserver', keyserver, '--send-keys']
        args.extend(keyids)
        self._handle_io(args, data, result, binary=True)
        logger.debug('send_keys result: %r', result.__dict__)
        data.close()
        return result
