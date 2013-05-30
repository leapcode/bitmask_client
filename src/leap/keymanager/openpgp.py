# -*- coding: utf-8 -*-
# openpgp.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""
Infrastructure for using OpenPGP keys in Key Manager.
"""
import logging
import os
import re
import shutil
import tempfile

from leap.common.check import leap_assert, leap_assert_type
from leap.keymanager import errors
from leap.keymanager.keys import (
    EncryptionKey,
    EncryptionScheme,
    is_address,
    build_key_from_dict,
    KEYMANAGER_KEY_TAG,
    TAGS_ADDRESS_PRIVATE_INDEX,
)
from leap.keymanager.gpg import GPGWrapper

logger = logging.getLogger(__name__)


#
# gpg wrapper and decorator
#

def temporary_gpgwrapper(keys=None):
    """
    Returns a unitary gpg wrapper that implements context manager
    protocol.

    :param key_data: ASCII armored key data.
    :type key_data: str

    :return: a GPGWrapper instance
    :rtype: GPGWrapper
    """
    # TODO do here checks on key_data
    return TempGPGWrapper(keys=keys)


def with_temporary_gpg(fun):
    """
    Decorator to add a temporary gpg wrapper as context
    to gpg related functions.

    Decorated functions are expected to return a function whose only
    argument is a gpgwrapper instance.
    """
    def wrapped(*args, **kwargs):
        """
        We extract the arguments passed to the wrapped function,
        run the function and do validations.
        We expect that the positional arguments are `data`,
        and an optional `key`.
        All the rest of arguments should be passed as named arguments
        to allow for a correct unpacking.
        """
        if len(args) == 2:
            keys = args[1] if isinstance(args[1], OpenPGPKey) else None
        else:
            keys = None

        # sign/verify keys passed as arguments
        sign = kwargs.get('sign', None)
        if sign:
            keys = [keys, sign]

        verify = kwargs.get('verify', None)
        if verify:
            keys = [keys, verify]

        # is the wrapped function sign or verify?
        fun_name = fun.__name__
        is_sign_function = True if fun_name == "sign" else False
        is_verify_function = True if fun_name == "verify" else False

        result = None

        with temporary_gpgwrapper(keys) as gpg:
            result = fun(*args, **kwargs)(gpg)

            # TODO: cleanup a little bit the
            # validation. maybe delegate to other
            # auxiliary functions for clarity.

            ok = getattr(result, 'ok', None)

            stderr = getattr(result, 'stderr', None)
            if stderr:
                logger.debug("%s" % (stderr,))

            if ok is False:
                raise errors.EncryptionDecryptionFailed(
                    'Failed to encrypt/decrypt in %s: %s' % (
                        fun.__name__,
                        stderr))

            if verify is not None:
                # A verify key has been passed
                if result.valid is False or \
                        verify.fingerprint != result.pubkey_fingerprint:
                    raise errors.InvalidSignature(
                        'Failed to verify signature with key %s: %s' %
                        (verify.key_id, stderr))

            if is_sign_function:
                # Specific validation for sign function
                privkey = gpg.list_keys(secret=True).pop()
                rfprint = result.fingerprint
                kfprint = privkey['fingerprint']
                if result.fingerprint is None:
                    raise errors.SignFailed(
                        'Failed to sign with key %s: %s' %
                        (privkey['keyid'], stderr))
                leap_assert(
                    result.fingerprint == kfprint,
                    'Signature and private key fingerprints mismatch: '
                    '%s != %s' %
                    (rfprint, kfprint))

            if is_verify_function:
                # Specific validation for verify function
                pubkey = gpg.list_keys().pop()
                valid = result.valid
                rfprint = result.fingerprint
                kfprint = pubkey['fingerprint']
                if valid is False or rfprint != kfprint:
                    raise errors.InvalidSignature(
                        'Failed to verify signature '
                        'with key %s.' % pubkey['keyid'])
                result = result.valid

            # ok, enough checks. let's return data if available
            if hasattr(result, 'data'):
                result = result.data
        return result
    return wrapped


class TempGPGWrapper(object):
    """
    A context manager returning a temporary GPG wrapper keyring, which
    contains exactly zero or one pubkeys, and zero or one privkeys.

    Temporary unitary keyrings allow the to use GPG's facilities for exactly
    one key. This function creates an empty temporary keyring and imports
    C{keys} if it is not None.
    """
    def __init__(self, keys=None):
        """
        :param keys: OpenPGP key, or list of.
        :type keys: OpenPGPKey or list of OpenPGPKeys
        """
        self._gpg = None
        if not keys:
            keys = list()
        if not isinstance(keys, list):
            keys = [keys]
        self._keys = keys
        for key in filter(None, keys):
            leap_assert_type(key, OpenPGPKey)

    def __enter__(self):
        """
        Calls the unitary gpgwrapper initializer

        :return: A GPG wrapper with a unitary keyring.
        :rtype: gnupg.GPG
        """
        self._build_keyring()
        return self._gpg

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Ensures the gpgwrapper is properly destroyed.
        """
        # TODO handle exceptions and log here
        self._destroy_keyring()

    def _build_keyring(self):
        """
        Create an empty GPG keyring and import C{keys} into it.

        :param keys: List of keys to add to the keyring.
        :type keys: list of OpenPGPKey

        :return: A GPG wrapper with a unitary keyring.
        :rtype: gnupg.GPG
        """
        privkeys = [key for key in self._keys if key and key.private is True]
        publkeys = [key for key in self._keys if key and key.private is False]
        # here we filter out public keys that have a correspondent
        # private key in the list because the private key_data by
        # itself is enough to also have the public key in the keyring,
        # and we want to count the keys afterwards.

        privaddrs = map(lambda privkey: privkey.address, privkeys)
        publkeys = filter(
            lambda pubkey: pubkey.address not in privaddrs, publkeys)

        listkeys = lambda: self._gpg.list_keys()
        listsecretkeys = lambda: self._gpg.list_keys(secret=True)

        self._gpg = GPGWrapper(gnupghome=tempfile.mkdtemp())
        leap_assert(len(listkeys()) is 0, 'Keyring not empty.')

        # import keys into the keyring:
        # concatenating ascii-armored keys, which is correctly
        # understood by the GPGWrapper.

        self._gpg.import_keys("".join(
            [x.key_data for x in publkeys + privkeys]))

        # assert the number of keys in the keyring
        leap_assert(
            len(listkeys()) == len(publkeys) + len(privkeys),
            'Wrong number of public keys in keyring: %d, should be %d)' %
            (len(listkeys()), len(publkeys) + len(privkeys)))
        leap_assert(
            len(listsecretkeys()) == len(privkeys),
            'Wrong number of private keys in keyring: %d, should be %d)' %
            (len(listsecretkeys()), len(privkeys)))

    def _destroy_keyring(self):
        """
        Securely erase a unitary keyring.
        """
        # TODO: implement some kind of wiping of data or a more
        # secure way that
        # does not write to disk.

        try:
            for secret in [True, False]:
                for key in self._gpg.list_keys(secret=secret):
                    self._gpg.delete_keys(
                        key['fingerprint'],
                        secret=secret)
            leap_assert(len(self._gpg.list_keys()) is 0, 'Keyring not empty!')

        except:
            raise

        finally:
            leap_assert(self._gpg.gnupghome != os.path.expanduser('~/.gnupg'),
                        "watch out! Tried to remove default gnupg home!")
            shutil.rmtree(self._gpg.gnupghome)


#
# API functions
#

@with_temporary_gpg
def encrypt_asym(data, key, passphrase=None, sign=None):
    """
    Encrypt C{data} using public @{key} and sign with C{sign} key.

    :param data: The data to be encrypted.
    :type data: str
    :param pubkey: The key used to encrypt.
    :type pubkey: OpenPGPKey
    :param sign: The key used for signing.
    :type sign: OpenPGPKey

    :return: The encrypted data.
    :rtype: str
    """
    leap_assert_type(key, OpenPGPKey)
    leap_assert(key.private is False, 'Key is not public.')
    if sign is not None:
        leap_assert_type(sign, OpenPGPKey)
        leap_assert(sign.private is True)

    # Here we cannot assert for correctness of sig because the sig is in
    # the ciphertext.
    # result.ok    - (bool) indicates if the operation succeeded
    # result.data  - (bool) contains the result of the operation

    return lambda gpg: gpg.encrypt(
        data, key.fingerprint,
        sign=sign.key_id if sign else None,
        passphrase=passphrase, symmetric=False)


@with_temporary_gpg
def decrypt_asym(data, key, passphrase=None, verify=None):
    """
    Decrypt C{data} using private @{key} and verify with C{verify} key.

    :param data: The data to be decrypted.
    :type data: str
    :param privkey: The key used to decrypt.
    :type privkey: OpenPGPKey
    :param verify: The key used to verify a signature.
    :type verify: OpenPGPKey

    :return: The decrypted data.
    :rtype: str

    @raise InvalidSignature: Raised if unable to verify the signature with
        C{verify} key.
    """
    leap_assert(key.private is True, 'Key is not private.')
    if verify is not None:
        leap_assert_type(verify, OpenPGPKey)
        leap_assert(verify.private is False)

    return lambda gpg: gpg.decrypt(
        data, passphrase=passphrase)


@with_temporary_gpg
def is_encrypted(data):
    """
    Return whether C{data} was encrypted using OpenPGP.

    :param data: The data we want to know about.
    :type data: str

    :return: Whether C{data} was encrypted using this wrapper.
    :rtype: bool
    """
    return lambda gpg: gpg.is_encrypted(data)


@with_temporary_gpg
def is_encrypted_asym(data):
    """
    Return whether C{data} was asymmetrically encrypted using OpenPGP.

    :param data: The data we want to know about.
    :type data: str

    :return: Whether C{data} was encrypted using this wrapper.
    :rtype: bool
    """
    return lambda gpg: gpg.is_encrypted_asym(data)


@with_temporary_gpg
def sign(data, privkey):
    """
    Sign C{data} with C{privkey}.

    :param data: The data to be signed.
    :type data: str

    :param privkey: The private key to be used to sign.
    :type privkey: OpenPGPKey

    :return: The ascii-armored signed data.
    :rtype: str
    """
    leap_assert_type(privkey, OpenPGPKey)
    leap_assert(privkey.private is True)

    # result.fingerprint - contains the fingerprint of the key used to
    #                      sign.
    return lambda gpg: gpg.sign(data, keyid=privkey.key_id)


@with_temporary_gpg
def verify(data, key):
    """
    Verify signed C{data} with C{pubkey}.

    :param data: The data to be verified.
    :type data: str

    :param pubkey: The public key to be used on verification.
    :type pubkey: OpenPGPKey

    :return: The ascii-armored signed data.
    :rtype: str
    """
    leap_assert_type(key, OpenPGPKey)
    leap_assert(key.private is False)

    return lambda gpg: gpg.verify(data)


#
# Helper functions
#


def _build_key_from_gpg(address, key, key_data):
    """
    Build an OpenPGPKey for C{address} based on C{key} from
    local gpg storage.

    ASCII armored GPG key data has to be queried independently in this
    wrapper, so we receive it in C{key_data}.

    :param address: The address bound to the key.
    :type address: str
    :param key: Key obtained from GPG storage.
    :type key: dict
    :param key_data: Key data obtained from GPG storage.
    :type key_data: str
    :return: An instance of the key.
    :rtype: OpenPGPKey
    """
    return OpenPGPKey(
        address,
        key_id=key['keyid'],
        fingerprint=key['fingerprint'],
        key_data=key_data,
        private=True if key['type'] == 'sec' else False,
        length=key['length'],
        expiry_date=key['expires'],
        validation=None,  # TODO: verify for validation.
    )


#
# The OpenPGP wrapper
#

class OpenPGPKey(EncryptionKey):
    """
    Base class for OpenPGP keys.
    """


class OpenPGPScheme(EncryptionScheme):
    """
    A wrapper for OpenPGP keys.
    """

    def __init__(self, soledad):
        """
        Initialize the OpenPGP wrapper.

        :param soledad: A Soledad instance for key storage.
        :type soledad: leap.soledad.Soledad
        """
        EncryptionScheme.__init__(self, soledad)

    def gen_key(self, address):
        """
        Generate an OpenPGP keypair bound to C{address}.

        :param address: The address bound to the key.
        :type address: str
        :return: The key bound to C{address}.
        :rtype: OpenPGPKey
        @raise KeyAlreadyExists: If key already exists in local database.
        """
        # make sure the key does not already exist
        leap_assert(is_address(address), 'Not an user address: %s' % address)
        try:
            self.get_key(address)
            raise errors.KeyAlreadyExists(address)
        except errors.KeyNotFound:
            pass

        def _gen_key(gpg):
            params = gpg.gen_key_input(
                key_type='RSA',
                key_length=4096,
                name_real=address,
                name_email=address,
                name_comment='Generated by LEAP Key Manager.')
            gpg.gen_key(params)
            pubkeys = gpg.list_keys()
            # assert for new key characteristics
            leap_assert(
                len(pubkeys) is 1,  # a unitary keyring!
                'Keyring has wrong number of keys: %d.' % len(pubkeys))
            key = gpg.list_keys(secret=True).pop()
            leap_assert(
                len(key['uids']) is 1,  # with just one uid!
                'Wrong number of uids for key: %d.' % len(key['uids']))
            leap_assert(
                re.match('.*<%s>$' % address, key['uids'][0]) is not None,
                'Key not correctly bound to address.')
            # insert both public and private keys in storage
            for secret in [True, False]:
                key = gpg.list_keys(secret=secret).pop()
                openpgp_key = _build_key_from_gpg(
                    address, key,
                    gpg.export_keys(key['fingerprint'], secret=secret))
                self.put_key(openpgp_key)

        with temporary_gpgwrapper() as gpg:
            # TODO: inspect result, or use decorator
            _gen_key(gpg)

        return self.get_key(address, private=True)

    def get_key(self, address, private=False):
        """
        Get key bound to C{address} from local storage.

        :param address: The address bound to the key.
        :type address: str
        :param private: Look for a private key instead of a public one?
        :type private: bool

        :return: The key bound to C{address}.
        :rtype: OpenPGPKey
        @raise KeyNotFound: If the key was not found on local storage.
        """
        leap_assert(is_address(address), 'Not an user address: %s' % address)
        doc = self._get_key_doc(address, private)
        if doc is None:
            raise errors.KeyNotFound(address)
        return build_key_from_dict(OpenPGPKey, address, doc.content)

    def put_ascii_key(self, key_data):
        """
        Put key contained in ascii-armored C{key_data} in local storage.

        :param key_data: The key data to be stored.
        :type key_data: str
        """
        leap_assert_type(key_data, str)
        # TODO: add more checks for correct key data.
        leap_assert(key_data is not None, 'Data does not represent a key.')

        def _put_ascii_key(gpg):
            gpg.import_keys(key_data)
            privkey = None
            pubkey = None

            try:
                privkey = gpg.list_keys(secret=True).pop()
            except IndexError:
                pass
            pubkey = gpg.list_keys(secret=False).pop()  # unitary keyring
            # extract adress from first uid on key
            match = re.match('.*<([\w.-]+@[\w.-]+)>.*', pubkey['uids'].pop())
            leap_assert(match is not None, 'No user address in key data.')
            address = match.group(1)
            if privkey is not None:
                match = re.match(
                    '.*<([\w.-]+@[\w.-]+)>.*', privkey['uids'].pop())
                leap_assert(match is not None, 'No user address in key data.')
                privaddress = match.group(1)
                leap_assert(
                    address == privaddress,
                    'Addresses in pub and priv key differ.')
                leap_assert(
                    pubkey['fingerprint'] == privkey['fingerprint'],
                    'Fingerprints for pub and priv key differ.')
                # insert private key in storage
                openpgp_privkey = _build_key_from_gpg(
                    address, privkey,
                    gpg.export_keys(privkey['fingerprint'], secret=True))
                self.put_key(openpgp_privkey)
            # insert public key in storage
            openpgp_pubkey = _build_key_from_gpg(
                address, pubkey,
                gpg.export_keys(pubkey['fingerprint'], secret=False))
            self.put_key(openpgp_pubkey)

        with temporary_gpgwrapper() as gpg:
            # TODO: inspect result, or use decorator
            _put_ascii_key(gpg)

    def put_key(self, key):
        """
        Put C{key} in local storage.

        :param key: The key to be stored.
        :type key: OpenPGPKey
        """
        doc = self._get_key_doc(key.address, private=key.private)
        if doc is None:
            self._soledad.create_doc_from_json(key.get_json())
        else:
            doc.set_json(key.get_json())
            self._soledad.put_doc(doc)

    def _get_key_doc(self, address, private=False):
        """
        Get the document with a key (public, by default) bound to C{address}.

        If C{private} is True, looks for a private key instead of a public.

        :param address: The address bound to the key.
        :type address: str
        :param private: Whether to look for a private key.
        :type private: bool
        :return: The document with the key or None if it does not exist.
        :rtype: leap.soledad.backends.leap_backend.LeapDocument
        """
        doclist = self._soledad.get_from_index(
            TAGS_ADDRESS_PRIVATE_INDEX,
            KEYMANAGER_KEY_TAG,
            address,
            '1' if private else '0')
        if len(doclist) is 0:
            return None
        leap_assert(
            len(doclist) is 1,
            'Found more than one %s key for address!' %
            'private' if private else 'public')
        return doclist.pop()

    def delete_key(self, key):
        """
        Remove C{key} from storage.

        :param key: The key to be removed.
        :type key: EncryptionKey
        """
        leap_assert(key.__class__ is OpenPGPKey, 'Wrong key type.')
        stored_key = self.get_key(key.address, private=key.private)
        if stored_key is None:
            raise errors.KeyNotFound(key)
        if stored_key.__dict__ != key.__dict__:
            raise errors.KeyAttributesDiffer(key)
        doc = self._get_key_doc(key.address, key.private)
        self._soledad.delete_doc(doc)
