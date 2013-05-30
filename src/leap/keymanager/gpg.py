# -*- coding: utf-8 -*-
# gpgwrapper.py
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
A GPG wrapper used to handle OpenPGP keys.

This is a temporary class that will be superseded by the a revised version of
python-gnupg.
"""


import os
import gnupg
import re
from gnupg import (
    logger,
    _is_sequence,
    _make_binary_stream,
)


class ListPackets():
    """
    Handle status messages for --list-packets.
    """

    def __init__(self, gpg):
        """
        Initialize the packet listing handling class.

        :param gpg: GPG object instance.
        :type gpg: gnupg.GPG
        """
        self.gpg = gpg
        self.nodata = None
        self.key = None
        self.need_passphrase = None
        self.need_passphrase_sym = None
        self.userid_hint = None

    def handle_status(self, key, value):
        """
        Handle one line of the --list-packets status message.

        :param key: The status message key.
        :type key: str
        :param value: The status message value.
        :type value: str
        """
        # TODO: write tests for handle_status
        if key == 'NODATA':
            self.nodata = True
        if key == 'ENC_TO':
            # This will only capture keys in our keyring. In the future we
            # may want to include multiple unknown keys in this list.
            self.key, _, _ = value.split()
        if key == 'NEED_PASSPHRASE':
            self.need_passphrase = True
        if key == 'NEED_PASSPHRASE_SYM':
            self.need_passphrase_sym = True
        if key == 'USERID_HINT':
            self.userid_hint = value.strip().split()


class GPGWrapper(gnupg.GPG):
    """
    This is a temporary class for handling GPG requests, and should be
    replaced by a more general class used throughout the project.
    """

    GNUPG_HOME = os.environ['HOME'] + "/.config/leap/gnupg"
    GNUPG_BINARY = "/usr/bin/gpg"  # this has to be changed based on OS

    def __init__(self, gpgbinary=GNUPG_BINARY, gnupghome=GNUPG_HOME,
                 verbose=False, use_agent=False, keyring=None, options=None):
        """
        Initialize a GnuPG process wrapper.

        :param gpgbinary: Name for GnuPG binary executable.
        :type gpgbinary: C{str}
        :param gpghome: Full pathname to directory containing the public and
            private keyrings.
        :type gpghome: C{str}
        :param keyring: Name of alternative keyring file to use. If specified,
            the default keyring is not used.
        :param verbose: Should some verbose info be output?
        :type verbose: bool
        :param use_agent: Should pass `--use-agent` to GPG binary?
        :type use_agent: bool
        :param keyring: Path for the keyring to use.
        :type keyring: str
        @options: A list of additional options to pass to the GPG binary.
        :type options: list

        @raise: RuntimeError with explanation message if there is a problem
            invoking gpg.
        """
        gnupg.GPG.__init__(self, gnupghome=gnupghome, gpgbinary=gpgbinary,
                           verbose=verbose, use_agent=use_agent,
                           keyring=keyring, options=options)
        self.result_map['list-packets'] = ListPackets

    def find_key_by_email(self, email, secret=False):
        """
        Find user's key based on their email.

        :param email: Email address of key being searched for.
        :type email: str
        :param secret: Should we search for a secret key?
        :type secret: bool

        :return: The fingerprint of the found key.
        :rtype: str
        """
        for key in self.list_keys(secret=secret):
            for uid in key['uids']:
                if re.search(email, uid):
                    return key
        raise LookupError("GnuPG public key for email %s not found!" % email)

    def find_key_by_subkey(self, subkey, secret=False):
        """
        Find user's key based on a subkey fingerprint.

        :param email: Subkey fingerprint of the key being searched for.
        :type email: str
        :param secret: Should we search for a secret key?
        :type secret: bool

        :return: The fingerprint of the found key.
        :rtype: str
        """
        for key in self.list_keys(secret=secret):
            for sub in key['subkeys']:
                if sub[0] == subkey:
                    return key
        raise LookupError(
            "GnuPG public key for subkey %s not found!" % subkey)

    def find_key_by_keyid(self, keyid, secret=False):
        """
        Find user's key based on the key ID.

        :param email: The key ID of the key being searched for.
        :type email: str
        :param secret: Should we search for a secret key?
        :type secret: bool

        :return: The fingerprint of the found key.
        :rtype: str
        """
        for key in self.list_keys(secret=secret):
            if keyid == key['keyid']:
                return key
        raise LookupError(
            "GnuPG public key for keyid %s not found!" % keyid)

    def find_key_by_fingerprint(self, fingerprint, secret=False):
        """
        Find user's key based on the key fingerprint.

        :param email: The fingerprint of the key being searched for.
        :type email: str
        :param secret: Should we search for a secret key?
        :type secret: bool

        :return: The fingerprint of the found key.
        :rtype: str
        """
        for key in self.list_keys(secret=secret):
            if fingerprint == key['fingerprint']:
                return key
        raise LookupError(
            "GnuPG public key for fingerprint %s not found!" % fingerprint)

    def encrypt(self, data, recipient, sign=None, always_trust=True,
                passphrase=None, symmetric=False):
        """
        Encrypt data using GPG.

        :param data: The data to be encrypted.
        :type data: str
        :param recipient: The address of the public key to be used.
        :type recipient: str
        :param sign: Should the encrypted content be signed?
        :type sign: bool
        :param always_trust: Skip key validation and assume that used keys
            are always fully trusted?
        :type always_trust: bool
        :param passphrase: The passphrase to be used if symmetric encryption
            is desired.
        :type passphrase: str
        :param symmetric: Should we encrypt to a password?
        :type symmetric: bool

        :return: An object with encrypted result in the `data` field.
        :rtype: gnupg.Crypt
        """
        # TODO: devise a way so we don't need to "always trust".
        return gnupg.GPG.encrypt(self, data, recipient, sign=sign,
                                 always_trust=always_trust,
                                 passphrase=passphrase,
                                 symmetric=symmetric,
                                 cipher_algo='AES256')

    def decrypt(self, data, always_trust=True, passphrase=None):
        """
        Decrypt data using GPG.

        :param data: The data to be decrypted.
        :type data: str
        :param always_trust: Skip key validation and assume that used keys
            are always fully trusted?
        :type always_trust: bool
        :param passphrase: The passphrase to be used if symmetric encryption
            is desired.
        :type passphrase: str

        :return: An object with decrypted result in the `data` field.
        :rtype: gnupg.Crypt
        """
        # TODO: devise a way so we don't need to "always trust".
        return gnupg.GPG.decrypt(self, data, always_trust=always_trust,
                                 passphrase=passphrase)

    def send_keys(self, keyserver, *keyids):
        """
        Send keys to a keyserver

        :param keyserver: The keyserver to send the keys to.
        :type keyserver: str
        :param keyids: The key ids to send.
        :type keyids: list

        :return: A list of keys sent to server.
        :rtype: gnupg.ListKeys
        """
        # TODO: write tests for this.
        # TODO: write a SendKeys class to handle status for this.
        result = self.result_map['list'](self)
        gnupg.logger.debug('send_keys: %r', keyids)
        data = gnupg._make_binary_stream("", self.encoding)
        args = ['--keyserver', keyserver, '--send-keys']
        args.extend(keyids)
        self._handle_io(args, data, result, binary=True)
        gnupg.logger.debug('send_keys result: %r', result.__dict__)
        data.close()
        return result

    def encrypt_file(self, file, recipients, sign=None,
                     always_trust=False, passphrase=None,
                     armor=True, output=None, symmetric=False,
                     cipher_algo=None):
        """
        Encrypt the message read from the file-like object 'file'.

        :param file: The file to be encrypted.
        :type data: file
        :param recipient: The address of the public key to be used.
        :type recipient: str
        :param sign: Should the encrypted content be signed?
        :type sign: bool
        :param always_trust: Skip key validation and assume that used keys
            are always fully trusted?
        :type always_trust: bool
        :param passphrase: The passphrase to be used if symmetric encryption
            is desired.
        :type passphrase: str
        :param armor: Create ASCII armored output?
        :type armor: bool
        :param output: Path of file to write results in.
        :type output: str
        :param symmetric: Should we encrypt to a password?
        :type symmetric: bool
        :param cipher_algo: Algorithm to use.
        :type cipher_algo: str

        :return: An object with encrypted result in the `data` field.
        :rtype: gnupg.Crypt
        """
        args = ['--encrypt']
        if symmetric:
            args = ['--symmetric']
            if cipher_algo:
                args.append('--cipher-algo %s' % cipher_algo)
        else:
            args = ['--encrypt']
            if not _is_sequence(recipients):
                recipients = (recipients,)
            for recipient in recipients:
                args.append('--recipient "%s"' % recipient)
        if armor:  # create ascii-armored output - set to False for binary
            args.append('--armor')
        if output:  # write the output to a file with the specified name
            if os.path.exists(output):
                os.remove(output)  # to avoid overwrite confirmation message
            args.append('--output "%s"' % output)
        if sign:
            args.append('--sign --default-key "%s"' % sign)
        if always_trust:
            args.append("--always-trust")
        result = self.result_map['crypt'](self)
        self._handle_io(args, file, result, passphrase=passphrase, binary=True)
        logger.debug('encrypt result: %r', result.data)
        return result

    def list_packets(self, data):
        """
        List the sequence of packets.

        :param data: The data to extract packets from.
        :type data: str

        :return: An object with packet info.
        :rtype ListPackets
        """
        args = ["--list-packets"]
        result = self.result_map['list-packets'](self)
        self._handle_io(
            args,
            _make_binary_stream(data, self.encoding),
            result,
        )
        return result

    def encrypted_to(self, data):
        """
        Return the key to which data is encrypted to.

        :param data: The data to be examined.
        :type data: str

        :return: The fingerprint of the key to which data is encrypted to.
        :rtype: str
        """
        # TODO: make this support multiple keys.
        result = self.list_packets(data)
        if not result.key:
            raise LookupError(
                "Content is not encrypted to a GnuPG key!")
        try:
            return self.find_key_by_keyid(result.key)
        except:
            return self.find_key_by_subkey(result.key)

    def is_encrypted_sym(self, data):
        """
        Say whether some chunk of data is encrypted to a symmetric key.

        :param data: The data to be examined.
        :type data: str

        :return: Whether data is encrypted to a symmetric key.
        :rtype: bool
        """
        result = self.list_packets(data)
        return bool(result.need_passphrase_sym)

    def is_encrypted_asym(self, data):
        """
        Say whether some chunk of data is encrypted to a private key.

        :param data: The data to be examined.
        :type data: str

        :return: Whether data is encrypted to a private key.
        :rtype: bool
        """
        result = self.list_packets(data)
        return bool(result.key)

    def is_encrypted(self, data):
        """
        Say whether some chunk of data is encrypted to a key.

        :param data: The data to be examined.
        :type data: str

        :return: Whether data is encrypted to a key.
        :rtype: bool
        """
        return self.is_encrypted_asym(data) or self.is_encrypted_sym(data)
