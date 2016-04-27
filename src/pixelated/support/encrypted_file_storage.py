#
# Copyright (c) 2014 ThoughtWorks, Inc.
#
# Pixelated is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pixelated is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.

from __future__ import with_statement

import hmac
import io
import os
from hashlib import sha256

from leap.soledad.client.crypto import decrypt_sym
from leap.soledad.client.crypto import encrypt_sym
from whoosh.filedb.filestore import FileStorage
from whoosh.filedb.structfile import BufferFile, StructFile
from whoosh.util import random_name


class DelayedCloseBytesIO(io.BytesIO):

    def __init__(self, name):
        super(DelayedCloseBytesIO, self).__init__()
        self._name = name
        self.shouldClose = False

    def close(self):

        self.shouldClose = True

    def explicit_close(self):
        super(DelayedCloseBytesIO, self).close()


class DelayedCloseStructFile(StructFile):

    def __init__(self, fileobj, name=None, onclose=None):
        super(DelayedCloseStructFile, self).__init__(fileobj, name, onclose)

    def close(self):
        """Closes the wrapped file.
        """

        if self.is_closed:
            raise Exception("This file is already closed")
        if self.onclose:
            self.onclose(self)
        if hasattr(self.file, "explicit_close"):
            self.file.explicit_close()
        self.is_closed = True


class EncryptedFileStorage(FileStorage):

    def __init__(self, path, masterkey=None):
        FileStorage.__init__(self, path, supports_mmap=False)
        self.masterkey = masterkey[:32]
        self.signkey = masterkey[32:]
        self._tmp_storage = self.temp_storage
        self.length_cache = {}
        self._open_files = {}

    def open_file(self, name, **kwargs):
        return self._open_encrypted_file(name)

    def create_file(self, name, excl=False, mode="w+b", **kwargs):
        f = DelayedCloseStructFile(DelayedCloseBytesIO(
            name), name=name, onclose=self._encrypt_index_on_close(name))
        f.is_real = False
        self._open_files[name] = f
        return f

    def delete_file(self, name):
        super(EncryptedFileStorage, self).delete_file(name)
        if name in self._open_files:
            del self._open_files[name]

    def temp_storage(self, name=None):
        name = name or "%s.tmp" % random_name()
        path = os.path.join(self.folder, name)
        return EncryptedFileStorage(path, self.masterkey).create()

    def file_length(self, name):
        return self.length_cache[name][0]

    def gen_mac(self, iv, ciphertext):
        verifiable_payload = ''.join((iv, ciphertext))
        return hmac.new(self.signkey, verifiable_payload, sha256).digest()

    def encrypt(self, content):
        iv, ciphertext = encrypt_sym(content, self.masterkey)
        mac = self.gen_mac(iv, ciphertext)
        return ''.join((mac, iv, ciphertext))

    def decrypt(self, payload):
        payload_mac, iv, ciphertext = payload[
            :32], payload[32:57], payload[57:]
        generated_mac = self.gen_mac(iv, ciphertext)
        if sha256(payload_mac).digest() != sha256(generated_mac).digest():
            raise Exception(
                "EncryptedFileStorage  - Error opening file. Wrong MAC")
        return decrypt_sym(ciphertext, self.masterkey, iv)

    def _encrypt_index_on_close(self, name):
        def wrapper(struct_file):
            struct_file.seek(0)
            content = struct_file.file.read()
            file_hash = sha256(content).digest()
            if name in self.length_cache and file_hash == self.length_cache[name][1]:
                return
            self.length_cache[name] = (len(content), file_hash)
            encrypted_content = self.encrypt(content)
            with open(self._fpath(name), 'w+b') as f:
                f.write(encrypted_content)

        return wrapper

    def _open_encrypted_file(self, name, onclose=lambda x: None):
        if not self.file_exists(name):
            if name in self._open_files:
                f = self._open_files[name]
                if not f.is_closed:
                    state = 'closed' if f.file.shouldClose else 'open'
                    if state == 'closed':
                        self._store_file(name, f.file.getvalue())
                        f.close()
                        del self._open_files[name]
            else:
                raise NameError(name)
        file_content = open(self._fpath(name), "rb").read()
        decrypted = self.decrypt(file_content)
        self.length_cache[name] = (len(decrypted), sha256(decrypted).digest())
        return BufferFile(buffer(decrypted), name=name, onclose=onclose)

    def _store_file(self, name, content):
        try:
            encrypted_content = self.encrypt(content)
            with open(self._fpath(name), 'w+b') as f:
                f.write(encrypted_content)
        except Exception, e:
            print e
            raise
