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

"""State for servers exposing a set of U1DB databases."""
import os
import errno

class ServerState(object):
    """Passed to a Request when it is instantiated.

    This is used to track server-side state, such as working-directory, open
    databases, etc.
    """

    def __init__(self):
        self._workingdir = None

    def set_workingdir(self, path):
        self._workingdir = path

    def _relpath(self, relpath):
        # Note: We don't want to allow absolute paths here, because we
        #       don't want to expose the filesystem. We should also check that
        #       relpath doesn't have '..' in it, etc.
        return self._workingdir + '/' + relpath

    def open_database(self, path):
        """Open a database at the given location."""
        from u1db.backends import sqlite_backend
        full_path = self._relpath(path)
        return sqlite_backend.SQLiteDatabase.open_database(full_path,
                                                           create=False)

    def check_database(self, path):
        """Check if the database at the given location exists.

        Simply returns if it does or raises DatabaseDoesNotExist.
        """
        db = self.open_database(path)
        db.close()

    def ensure_database(self, path):
        """Ensure database at the given location."""
        from u1db.backends import sqlite_backend
        full_path = self._relpath(path)
        db = sqlite_backend.SQLiteDatabase.open_database(full_path,
                                                         create=True)
        return db, db._replica_uid

    def delete_database(self, path):
        """Delete database at the given location."""
        from u1db.backends import sqlite_backend
        full_path = self._relpath(path)
        sqlite_backend.SQLiteDatabase.delete_database(full_path)
