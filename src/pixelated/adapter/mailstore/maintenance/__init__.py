#
# Copyright (c) 2015 ThoughtWorks, Inc.
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
from leap.keymanager.keys import KEY_TYPE_KEY, KEY_PRIVATE_KEY, KEY_FINGERPRINT_KEY, KEY_ADDRESS_KEY
from leap.keymanager.openpgp import OpenPGPKey

from twisted.internet import defer
import logging


TYPE_OPENPGP_KEY = 'OpenPGPKey'
TYPE_OPENPGP_ACTIVE = 'OpenPGPKey-active'

KEY_DOC_TYPES = {TYPE_OPENPGP_ACTIVE, TYPE_OPENPGP_KEY}

logger = logging.getLogger(__name__)


def _is_key_doc(doc):
    return doc.content.get(KEY_TYPE_KEY, None) in KEY_DOC_TYPES


def _is_private_key_doc(doc):
    return _is_key_doc(doc) and doc.content.get(KEY_PRIVATE_KEY, False)


def _is_active_key_doc(doc):
    return _is_key_doc(doc) and doc.content.get(KEY_TYPE_KEY, None) == TYPE_OPENPGP_ACTIVE


def _is_public_key(doc):
    return _is_key_doc(doc) and not doc.content.get(KEY_PRIVATE_KEY, False)


def _key_fingerprint(doc):
    return doc.content.get(KEY_FINGERPRINT_KEY, None)


def _address(doc):
    return doc.content.get(KEY_ADDRESS_KEY, None)


class SoledadMaintenance(object):

    def __init__(self, soledad):
        self._soledad = soledad

    @defer.inlineCallbacks
    def repair(self):
        _, docs = yield self._soledad.get_all_docs()

        private_key_fingerprints = self._key_fingerprints_with_private_key(
            docs)

        for doc in docs:
            if _is_key_doc(doc) and _key_fingerprint(doc) not in private_key_fingerprints:
                logger.warn('Deleting doc %s for key %s of <%s>' %
                            (doc.doc_id, _key_fingerprint(doc), _address(doc)))
                yield self._soledad.delete_doc(doc)

        yield self._repair_missing_active_docs(docs, private_key_fingerprints)

    @defer.inlineCallbacks
    def _repair_missing_active_docs(self, docs, private_key_fingerprints):
        missing = self._missing_active_docs(docs, private_key_fingerprints)
        for fingerprint in missing:
            emails = self._emails_for_key_fingerprint(docs, fingerprint)
            for email in emails:
                logger.warn('Re-creating active doc for key %s, email %s' %
                            (fingerprint, email))
                yield self._soledad.create_doc_from_json(OpenPGPKey(email, fingerprint=fingerprint, private=False).get_active_json())

    def _key_fingerprints_with_private_key(self, docs):
        return [doc.content[KEY_FINGERPRINT_KEY] for doc in docs if _is_private_key_doc(doc)]

    def _missing_active_docs(self, docs, private_key_fingerprints):
        active_doc_ids = self._active_docs_for_key_fingerprint(docs)

        return set([private_key_fingerprint for private_key_fingerprint in private_key_fingerprints if private_key_fingerprint not in active_doc_ids])

    def _emails_for_key_fingerprint(self, docs, fingerprint):
        for doc in docs:
            if _is_private_key_doc(doc) and _key_fingerprint(doc) == fingerprint:
                email = _address(doc)
                if email is None:
                    return []
                if isinstance(email, list):
                    return email
                return [email]

    def _active_docs_for_key_fingerprint(self, docs):
        return [doc.content[KEY_FINGERPRINT_KEY] for doc in docs if _is_active_key_doc(doc) and _is_public_key(doc)]
