import os
import logging

from pixelated.adapter.mailstore.leap_attachment_store import LeapAttachmentStore
from pixelated.adapter.mailstore.searchable_mailstore import SearchableMailStore
from pixelated.adapter.services.mail_service import MailService
from pixelated.adapter.model.mail import InputMail
from pixelated.adapter.services.mail_sender import MailSender
from pixelated.adapter.search import SearchEngine
from pixelated.adapter.services.draft_service import DraftService
from pixelated.adapter.listeners.mailbox_indexer_listener import listen_all_mailboxes
from twisted.internet import defer
from pixelated.adapter.search.index_storage_key import SearchIndexStorageKey
from pixelated.adapter.services.feedback_service import FeedbackService

logger = logging.getLogger(__name__)


class Services(object):

    def __init__(self, leap_session):
        self._leap_home = leap_session.config.leap_home
        self._leap_session = leap_session

    @defer.inlineCallbacks
    def setup(self):
        search_index_storage_key = self._setup_search_index_storage_key(
            self._leap_session.soledad)
        yield self._setup_search_engine(self._leap_session.user_auth.uuid, search_index_storage_key)

        self._wrap_mail_store_with_indexing_mail_store(self._leap_session)

        yield listen_all_mailboxes(self._leap_session.account, self.search_engine, self._leap_session.mail_store)

        self.mail_service = self._setup_mail_service(self.search_engine)

        self.keymanager = self._leap_session.nicknym
        self.draft_service = self._setup_draft_service(
            self._leap_session.mail_store)
        self.feedback_service = self._setup_feedback_service()

        yield self._index_all_mails()

    def close(self):
        self._leap_session.close()

    def _wrap_mail_store_with_indexing_mail_store(self, leap_session):
        leap_session.mail_store = SearchableMailStore(
            leap_session.mail_store, self.search_engine)

    @defer.inlineCallbacks
    def _index_all_mails(self):
        all_mails = yield self.mail_service.all_mails()
        self.search_engine.index_mails(all_mails)

    @defer.inlineCallbacks
    def _setup_search_engine(self, namespace, search_index_storage_key):
        key_unicode = yield search_index_storage_key.get_or_create_key()
        key = str(key_unicode)
        logger.debug('The key len is: %s' % len(key))
        user_id = self._leap_session.user_auth.uuid
        user_folder = os.path.join(self._leap_home, user_id)
        search_engine = SearchEngine(key, user_home=user_folder)
        self.search_engine = search_engine

    def _setup_mail_service(self, search_engine):
        pixelated_mail_sender = MailSender(
            self._leap_session.smtp_config, self._leap_session.nicknym.keymanager)

        return MailService(
            pixelated_mail_sender,
            self._leap_session.mail_store,
            search_engine,
            self._leap_session.account_email(),
            LeapAttachmentStore(self._leap_session.soledad))

    def _setup_draft_service(self, mail_store):
        return DraftService(mail_store)

    def _setup_search_index_storage_key(self, soledad):
        return SearchIndexStorageKey(soledad)

    def _setup_feedback_service(self):
        return FeedbackService(self._leap_session)
