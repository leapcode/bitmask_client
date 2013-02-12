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
from pysqlcipher import dbapi2
import time

from u1db.backends.sqlite_backend import (
    SQLiteDatabase,
    SQLitePartialExpandDatabase,
)
from u1db import (
    errors,
)

from leap.soledad.backends.leap_backend import LeapDocument


def open(path, password, create=True, document_factory=None, soledad=None):
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
        path, password, create=create, document_factory=document_factory,
        soledad=soledad)


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

    def __init__(self, sqlite_file, password, document_factory=None,
                 soledad=None):
        """Create a new sqlcipher file."""
        self._check_if_db_is_encrypted(sqlite_file)
        self._db_handle = dbapi2.connect(sqlite_file)
        SQLCipherDatabase.set_pragma_key(self._db_handle, password)
        self._real_replica_uid = None
        self._ensure_schema()
        self._soledad = soledad

        def factory(doc_id=None, rev=None, json='{}', has_conflicts=False,
                    encrypted_json=None, syncable=True):
            return LeapDocument(doc_id=doc_id, rev=rev, json=json,
                                has_conflicts=has_conflicts,
                                encrypted_json=encrypted_json,
                                syncable=syncable, soledad=self._soledad)
        self.set_document_factory(factory)

    def _check_if_db_is_encrypted(self, sqlite_file):
        if not os.path.exists(sqlite_file):
            return
        else:
            try:
                # try to open an encrypted database with the regular u1db
                # backend should raise a DatabaseError exception.
                SQLitePartialExpandDatabase(sqlite_file)
                raise DatabaseIsNotEncrypted()
            except dbapi2.DatabaseError:
                pass

    @classmethod
    def _open_database(cls, sqlite_file, password, document_factory=None,
                       soledad=None):
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
            sqlite_file, password, document_factory=document_factory,
            soledad=soledad)

    @classmethod
    def open_database(cls, sqlite_file, password, create, backend_cls=None,
                      document_factory=None, soledad=None):
        try:
            return cls._open_database(sqlite_file, password,
                                      document_factory=document_factory,
                                      soledad=soledad)
        except errors.DatabaseDoesNotExist:
            if not create:
                raise
            if backend_cls is None:
                # default is SQLCipherPartialExpandDatabase
                backend_cls = SQLCipherDatabase
            return backend_cls(sqlite_file, password,
                               document_factory=document_factory,
                               soledad=soledad)

    def sync(self, url, creds=None, autocreate=True):
        """
        Synchronize encrypted documents with remote replica exposed at url.
        """
        from u1db.sync import Synchronizer
        from leap.soledad.backends.leap_backend import LeapSyncTarget
        return Synchronizer(
            self,
            LeapSyncTarget(url,
                           creds=creds,
                           soledad=self._soledad)).sync(autocreate=autocreate)

    def _extra_schema_init(self, c):
        c.execute(
            'ALTER TABLE document '
            'ADD COLUMN syncable BOOL NOT NULL DEFAULT TRUE')

    def _put_and_update_indexes(self, old_doc, doc):
        super(SQLCipherDatabase, self)._put_and_update_indexes(old_doc, doc)
        c = self._db_handle.cursor()
        c.execute('UPDATE document SET syncable=? WHERE doc_id=?',
                  (doc.syncable, doc.doc_id))

    def _get_doc(self, doc_id, check_for_conflicts=False):
        doc = super(SQLCipherDatabase, self)._get_doc(doc_id,
                                                      check_for_conflicts)
        if doc:
            c = self._db_handle.cursor()
            c.execute('SELECT syncable FROM document WHERE doc_id=?',
                      (doc.doc_id,))
            doc.syncable = bool(c.fetchone()[0])
        return doc


SQLiteDatabase.register_implementation(SQLCipherDatabase)
