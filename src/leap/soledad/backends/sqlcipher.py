# Copyright 2011 Canonical Ltd.
#
# This file is part of u1db.
#
# u1db is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# u1db is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with u1db.  If not, see <http://www.gnu.org/licenses/>.

"""A U1DB implementation that uses SQLCipher as its persistence layer."""

import os
from sqlite3 import dbapi2, DatabaseError
import time

from u1db.backends.sqlite_backend import SQLitePartialExpandDatabase
from u1db import (
    Document,
    errors,
)


def open(path, password, create, document_factory=None):
    """Open a database at the given location.

    Will raise u1db.errors.DatabaseDoesNotExist if create=False and the
    database does not already exist.

    :param path: The filesystem path for the database to open.
    :param create: True/False, should the database be created if it doesn't
        already exist?
    :param document_factory: A function that will be called with the same
        parameters as Document.__init__.
    :return: An instance of Database.
    """
    return SQLCipherDatabase.open_database(
        path, password, create=create, document_factory=document_factory)


class DatabaseIsNotEncrypted(Exception):
    """
    Exception raised when trying to open non-encrypted databases.
    """
    pass


class SQLCipherDatabase(SQLitePartialExpandDatabase):
    """A U1DB implementation that uses SQLCipher as its persistence layer."""

    _index_storage_value = 'expand referenced encrypted'


    @classmethod
    def set_pragma_key(cls, db_handle, key):
       db_handle.cursor().execute("PRAGMA key = '%s'" % key)


    def __init__(self, sqlite_file, password, document_factory=None):
        """Create a new sqlcipher file."""
        self._check_if_db_is_encrypted(sqlite_file)
        self._db_handle = dbapi2.connect(sqlite_file)
        SQLCipherDatabase.set_pragma_key(self._db_handle, password)
        self._real_replica_uid = None
        self._ensure_schema()
        self._factory = document_factory or Document


    def _check_if_db_is_encrypted(self, sqlite_file):
        if not os.path.exists(sqlite_file):
            return
        else:
            try:
                # try to open an encrypted database with the regular u1db backend
                # should raise a DatabaseError exception.
                SQLitePartialExpandDatabase(sqlite_file)
                raise DatabaseIsNotEncrypted()
            except DatabaseError:
                pass


    @classmethod
    def _open_database(cls, sqlite_file, password, document_factory=None):
        if not os.path.isfile(sqlite_file):
            raise errors.DatabaseDoesNotExist()
        tries = 2
        while True:
            # Note: There seems to be a bug in sqlite 3.5.9 (with python2.6)
            #       where without re-opening the database on Windows, it
            #       doesn't see the transaction that was just committed
            db_handle = dbapi2.connect(sqlite_file)
            SQLCipherDatabase.set_pragma_key(db_handle, password)
            c = db_handle.cursor()
            v, err = cls._which_index_storage(c)
            db_handle.close()
            if v is not None:
                break
            # possibly another process is initializing it, wait for it to be
            # done
            if tries == 0:
                raise err  # go for the richest error?
            tries -= 1
            time.sleep(cls.WAIT_FOR_PARALLEL_INIT_HALF_INTERVAL)
        return SQLCipherDatabase._sqlite_registry[v](
            sqlite_file, password, document_factory=document_factory)


    @classmethod
    def open_database(cls, sqlite_file, password, create, backend_cls=None,
                      document_factory=None):
        try:
            return cls._open_database(sqlite_file, password,
                                      document_factory=document_factory)
        except errors.DatabaseDoesNotExist:
            if not create:
                raise
            if backend_cls is None:
                # default is SQLCipherPartialExpandDatabase
                backend_cls = SQLCipherDatabase
            return backend_cls(sqlite_file, password,
                               document_factory=document_factory)


    @staticmethod
    def register_implementation(klass):
        """Register that we implement an SQLCipherDatabase.

        The attribute _index_storage_value will be used as the lookup key.
        """
        SQLCipherDatabase._sqlite_registry[klass._index_storage_value] = klass


SQLiteDatabase.register_implementation(SQLCipherDatabase)

