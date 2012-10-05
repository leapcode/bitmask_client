import os

import keyring

#############
# Disclaimer
#############
# This currently is not a keyring, it's more like a joke.
# No, seriously.
# We're affected by this **bug**

# https://bitbucket.org/kang/python-keyring-lib/issue/65/dbusexception-method-opensession-with

# so using the gnome keyring does not seem feasible right now.
# I thought this was the next best option to store secrets in plain sight.

# in the future we should move to use the gnome/kde/macosx/win keyrings.


class LeapCryptedFileKeyring(keyring.backend.CryptedFileKeyring):

    filename = os.path.expanduser("~/.config/leap/.secrets")

    def __init__(self, seed=None):
        self.seed = seed

    def _get_new_password(self):
        # XXX every time this method is called,
        # $deity kills a kitten.
        return "secret%s" % self.seed

    def _init_file(self):
        self.keyring_key = self._get_new_password()
        self.set_password('keyring_setting', 'pass_ref', 'pass_ref_value')

    def _unlock(self):
        self.keyring_key = self._get_new_password()
        print 'keyring key ', self.keyring_key
        try:
            ref_pw = self.get_password(
                'keyring_setting',
                'pass_ref')
            print 'ref pw ', ref_pw
            assert ref_pw == "pass_ref_value"
        except AssertionError:
            self._lock()
            raise ValueError('Incorrect password')


def leap_set_password(key, value, seed="xxx"):
    keyring.set_keyring(LeapCryptedFileKeyring(seed=seed))
    keyring.set_password('leap', key, value)


def leap_get_password(key, seed="xxx"):
    keyring.set_keyring(LeapCryptedFileKeyring(seed=seed))
    return keyring.get_password('leap', key)


if __name__ == "__main__":
    leap_set_password('test', 'bar')
    passwd = leap_get_password('test')
    assert passwd == 'bar'
