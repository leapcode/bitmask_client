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
from email import encoders
from email.mime.nonmultipart import MIMENonMultipart
from email.mime.multipart import MIMEMultipart
from leap.mail.mail import Message

from twisted.internet import defer

from pixelated.adapter.model.mail import InputMail
from pixelated.adapter.model.status import Status
from pixelated.adapter.services.tag_service import extract_reserved_tags
from leap.mail.adaptors.soledad import SoledadMailAdaptor


class MailService(object):

    def __init__(self, mail_sender, mail_store, search_engine, account_email, attachment_store):
        self.mail_store = mail_store
        self.search_engine = search_engine
        self.mail_sender = mail_sender
        self.account_email = account_email
        self.attachment_store = attachment_store

    @defer.inlineCallbacks
    def all_mails(self):
        mails = yield self.mail_store.all_mails(gracefully_ignore_errors=True)
        defer.returnValue(mails)

    def save_attachment(self, content, content_type):
        return self.attachment_store.add_attachment(content, content_type)

    @defer.inlineCallbacks
    def mails(self, query, window_size, page):
        mail_ids, total = self.search_engine.search(query, window_size, page)

        try:
            mails = yield self.mail_store.get_mails(mail_ids)
            defer.returnValue((mails, total))
        except Exception, e:
            import traceback
            traceback.print_exc()
            raise

    @defer.inlineCallbacks
    def update_tags(self, mail_id, new_tags):
        new_tags = self._filter_white_space_tags(new_tags)
        reserved_words = extract_reserved_tags(new_tags)
        if len(reserved_words):
            raise ValueError(
                'None of the following words can be used as tags: ' + ' '.join(reserved_words))
        new_tags = self._favor_existing_tags_casing(new_tags)
        mail = yield self.mail(mail_id)
        mail.tags = set(new_tags)
        yield self.mail_store.update_mail(mail)

        defer.returnValue(mail)

    def _filter_white_space_tags(self, tags):
        return [tag.strip() for tag in tags if not tag.isspace()]

    def _favor_existing_tags_casing(self, new_tags):
        current_tags = [tag['name'] for tag in self.search_engine.tags(
            query='', skip_default_tags=True)]
        current_tags_lower = [tag.lower() for tag in current_tags]

        def _use_current_casing(new_tag_lower):
            return current_tags[current_tags_lower.index(new_tag_lower)]

        return [_use_current_casing(new_tag.lower()) if new_tag.lower() in current_tags_lower else new_tag for new_tag in new_tags]

    def mail(self, mail_id):
        return self.mail_store.get_mail(mail_id, include_body=True)

    def attachment(self, attachment_id):
        return self.attachment_store.get_mail_attachment(attachment_id)

    @defer.inlineCallbacks
    def mail_exists(self, mail_id):
        try:
            mail = yield self.mail_store.get_mail(mail_id, include_body=False)
            defer.returnValue(mail is not None)
        except Exception, e:
            defer.returnValue(False)

    @defer.inlineCallbacks
    def send_mail(self, content_dict):
        mail = InputMail.from_dict(content_dict, self.account_email)
        draft_id = content_dict.get('ident')
        yield self.mail_sender.sendmail(mail)

        sent_mail = yield self.move_to_sent(draft_id, mail)
        defer.returnValue(sent_mail)

    @defer.inlineCallbacks
    def move_to_sent(self, last_draft_ident, mail):
        if last_draft_ident:
            try:
                yield self.mail_store.delete_mail(last_draft_ident)
            except Exception as error:
                pass
        sent_mail = yield self.mail_store.add_mail('SENT', mail.raw)
        sent_mail.flags.add(Status.SEEN)
        yield self.mail_store.update_mail(sent_mail)
        defer.returnValue(sent_mail)

    @defer.inlineCallbacks
    def mark_as_read(self, mail_id):
        mail = yield self.mail(mail_id)
        mail.flags.add(Status.SEEN)
        yield self.mail_store.update_mail(mail)

    @defer.inlineCallbacks
    def mark_as_unread(self, mail_id):
        mail = yield self.mail(mail_id)
        mail.flags.remove(Status.SEEN)
        yield self.mail_store.update_mail(mail)

    @defer.inlineCallbacks
    def delete_mail(self, mail_id):
        mail = yield self.mail(mail_id)
        if mail is not None:
            if mail.mailbox_name.upper() in (u'TRASH', u'DRAFTS'):
                yield self.mail_store.delete_mail(mail_id)
            else:
                yield self.mail_store.move_mail_to_mailbox(mail_id, 'TRASH')

    @defer.inlineCallbacks
    def recover_mail(self, mail_id):
        yield self.mail_store.move_mail_to_mailbox(mail_id, 'INBOX')

    @defer.inlineCallbacks
    def archive_mail(self, mail_id):
        yield self.mail_store.add_mailbox('ARCHIVE')
        yield self.mail_store.move_mail_to_mailbox(mail_id, 'ARCHIVE')

    @defer.inlineCallbacks
    def delete_permanent(self, mail_id):
        yield self.mail_store.delete_mail(mail_id)
