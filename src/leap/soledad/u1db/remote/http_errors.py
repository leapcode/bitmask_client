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

"""Information about the encoding of errors over HTTP."""

from u1db import (
    errors,
    )


# error wire descriptions mapping to HTTP status codes
wire_description_to_status = dict([
    (errors.InvalidDocId.wire_description, 400),
    (errors.MissingDocIds.wire_description, 400),
    (errors.Unauthorized.wire_description, 401),
    (errors.DocumentTooBig.wire_description, 403),
    (errors.UserQuotaExceeded.wire_description, 403),
    (errors.SubscriptionNeeded.wire_description, 403),
    (errors.DatabaseDoesNotExist.wire_description, 404),
    (errors.DocumentDoesNotExist.wire_description, 404),
    (errors.DocumentAlreadyDeleted.wire_description, 404),
    (errors.RevisionConflict.wire_description, 409),
    (errors.InvalidGeneration.wire_description, 409),
    (errors.InvalidTransactionId.wire_description, 409),
    (errors.Unavailable.wire_description, 503),
# without matching exception
    (errors.DOCUMENT_DELETED, 404)
])


ERROR_STATUSES = set(wire_description_to_status.values())
# 400 included explicitly for tests
ERROR_STATUSES.add(400)
