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
from leap.soledad.client import Soledad
from leap.soledad.common.crypto import WrongMacError, UnknownMacMethodError


class SoledadDiscoverException(Exception):

    def __init__(self, *args, **kwargs):
        super(SoledadDiscoverException, self).__init__(*args, **kwargs)


class SoledadWrongPassphraseException(Exception):

    def __init__(self, *args, **kwargs):
        super(SoledadWrongPassphraseException, self).__init__(*args, **kwargs)


class SoledadFactory(object):

    @classmethod
    def create(cls, user_token, user_uuid, encryption_passphrase, secrets, local_db, server_url, api_cert):
        try:
            return Soledad(user_uuid,
                           passphrase=unicode(encryption_passphrase),
                           secrets_path=secrets,
                           local_db_path=local_db,
                           server_url=server_url,
                           cert_file=api_cert,
                           shared_db=None,
                           auth_token=user_token,
                           defer_encryption=False)

        except (WrongMacError, UnknownMacMethodError), e:
            raise SoledadWrongPassphraseException(e)
