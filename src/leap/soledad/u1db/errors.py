# Copyright 2011-2012 Canonical Ltd.
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

"""A list of errors that u1db can raise."""


class U1DBError(Exception):
    """Generic base class for U1DB errors."""

    # description/tag for identifying the error during transmission (http,...)
    wire_description = "error"

    def __init__(self, message=None):
        self.message = message


class RevisionConflict(U1DBError):
    """The document revisions supplied does not match the current version."""

    wire_description = "revision conflict"


class InvalidJSON(U1DBError):
    """Content was not valid json."""


class InvalidContent(U1DBError):
    """Content was not a python dictionary."""


class InvalidDocId(U1DBError):
    """A document was requested with an invalid document identifier."""

    wire_description = "invalid document id"


class MissingDocIds(U1DBError):
    """Needs document ids."""

    wire_description = "missing document ids"


class DocumentTooBig(U1DBError):
    """Document exceeds the maximum document size for this database."""

    wire_description = "document too big"


class UserQuotaExceeded(U1DBError):
    """Document exceeds the maximum document size for this database."""

    wire_description = "user quota exceeded"


class SubscriptionNeeded(U1DBError):
    """User needs a subscription to be able to use this replica.."""

    wire_description = "user needs subscription"


class InvalidTransactionId(U1DBError):
    """Invalid transaction for generation."""

    wire_description = "invalid transaction id"


class InvalidGeneration(U1DBError):
    """Generation was previously synced with a different transaction id."""

    wire_description = "invalid generation"


class ConflictedDoc(U1DBError):
    """The document is conflicted, you must call resolve before put()"""


class InvalidValueForIndex(U1DBError):
    """The values supplied does not match the index definition."""


class InvalidGlobbing(U1DBError):
    """Raised if wildcard matches are not strictly at the tail of the request.
    """


class DocumentDoesNotExist(U1DBError):
    """The document does not exist."""

    wire_description = "document does not exist"


class DocumentAlreadyDeleted(U1DBError):
    """The document was already deleted."""

    wire_description = "document already deleted"


class DatabaseDoesNotExist(U1DBError):
    """The database does not exist."""

    wire_description = "database does not exist"


class IndexNameTakenError(U1DBError):
    """The given index name is already taken."""


class IndexDefinitionParseError(U1DBError):
    """The index definition cannot be parsed."""


class IndexDoesNotExist(U1DBError):
    """No index of that name exists."""


class Unauthorized(U1DBError):
    """Request wasn't authorized properly."""

    wire_description = "unauthorized"


class HTTPError(U1DBError):
    """Unspecific HTTP errror."""

    wire_description = None

    def __init__(self, status, message=None, headers={}):
        self.status = status
        self.message = message
        self.headers = headers

    def __str__(self):
        if not self.message:
            return "HTTPError(%d)" % self.status
        else:
            return "HTTPError(%d, %r)" % (self.status, self.message)


class Unavailable(HTTPError):
    """Server not available not serve request."""

    wire_description = "unavailable"

    def __init__(self, message=None, headers={}):
        super(Unavailable, self).__init__(503, message, headers)

    def __str__(self):
        if not self.message:
            return "Unavailable()"
        else:
            return "Unavailable(%r)" % self.message


class BrokenSyncStream(U1DBError):
    """Unterminated or otherwise broken sync exchange stream."""

    wire_description = None


class UnknownAuthMethod(U1DBError):
    """Unknown auhorization method."""

    wire_description = None


# mapping wire (transimission) descriptions/tags for errors to the exceptions
wire_description_to_exc = dict(
    (x.wire_description, x) for x in globals().values()
            if getattr(x, 'wire_description', None) not in (None, "error")
)
wire_description_to_exc["error"] = U1DBError


#
# wire error descriptions not corresponding to an exception
DOCUMENT_DELETED = "document deleted"
