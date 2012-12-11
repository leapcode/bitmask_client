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

import errno
import os
try:
    import simplejson as json
except ImportError:
    import json  # noqa
from sqlite3 import dbapi2
import sys
import time
import uuid

import pkg_resources

from u1db.backends import CommonBackend, CommonSyncTarget
from u1db.backends.sqlite_backend import SQLitePartialExpandDatabase
from u1db import (
    Document,
    errors,
    query_parser,
    vectorclock,
    )


def open(path, create, document_factory=None, password=None):
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
    from u1db.backends import sqlite_backend
    return sqlite_backend.SQLCipherDatabase.open_database(
        path, create=create, document_factory=document_factory, password=password)


class SQLCipherDatabase(SQLitePartialExpandDatabase):
    """A U1DB implementation that uses SQLCipher as its persistence layer."""

    _index_storage_value = 'expand referenced encrypted'


    @classmethod
    def set_pragma_key(cls, db_handle, key):
       db_handle.cursor().execute("PRAGMA key = '%s'" % key)

    def __init__(self, sqlite_file, document_factory=None, password=None):
        """Create a new sqlite file."""
        self._db_handle = dbapi2.connect(sqlite_file)
        if password:
            SQLiteDatabase.set_pragma_key(self._db_handle, password)
        self._real_replica_uid = None
        self._ensure_schema()
        self._factory = document_factory or Document

    @classmethod
    def _open_database(cls, sqlite_file, document_factory=None, password=None):
        if not os.path.isfile(sqlite_file):
            raise errors.DatabaseDoesNotExist()
        tries = 2
        while True:
            # Note: There seems to be a bug in sqlite 3.5.9 (with python2.6)
            #       where without re-opening the database on Windows, it
            #       doesn't see the transaction that was just committed
            db_handle = dbapi2.connect(sqlite_file)
            if password:
                SQLiteDatabase.set_pragma_key(db_handle, password)
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
            sqlite_file, document_factory=document_factory)

    @classmethod
    def open_database(cls, sqlite_file, create, backend_cls=None,
                      document_factory=None, password=None):
        try:
            return cls._open_database(sqlite_file,
                                      document_factory=document_factory,
                                      password=password)
        except errors.DatabaseDoesNotExist:
            if not create:
                raise
            if backend_cls is None:
                # default is SQLCipherPartialExpandDatabase
                backend_cls = SQLCipherDatabase
            return backend_cls(sqlite_file, document_factory=document_factory,
                               password=password)

    @staticmethod
    def register_implementation(klass):
        """Register that we implement an SQLCipherDatabase.

        The attribute _index_storage_value will be used as the lookup key.
        """
        SQLCipherDatabase._sqlite_registry[klass._index_storage_value] = klass


SQLCipherDatabase.register_implementation(SQLCipherDatabase)
