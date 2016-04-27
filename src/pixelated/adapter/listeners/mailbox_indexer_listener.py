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
# MERCHANTABILITY or FITNESS FOR A PCULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.
import logging
from twisted.internet import defer


logger = logging.getLogger(__name__)


class MailboxIndexerListener(object):
    """ Listens for new mails, keeping the index updated """

    @classmethod
    @defer.inlineCallbacks
    def listen(cls, account, mailbox_name, mail_store, search_engine):
        listener = MailboxIndexerListener(
            mailbox_name, mail_store, search_engine)
        mail_collection = yield account.get_collection_by_mailbox(mailbox_name)
        mail_collection.addListener(listener)

        defer.returnValue(listener)

    def __init__(self, mailbox_name, mail_store, search_engine):
        self.mailbox_name = mailbox_name
        self.mail_store = mail_store
        self.search_engine = search_engine

    @defer.inlineCallbacks
    def notify_new(self):
        try:
            indexed_idents = set(self.search_engine.search(
                'tag:' + self.mailbox_name.lower(), all_mails=True))
            soledad_idents = yield self.mail_store.get_mailbox_mail_ids(self.mailbox_name)
            soledad_idents = set(soledad_idents)

            missing_idents = soledad_idents.difference(indexed_idents)

            self.search_engine.index_mails((yield self.mail_store.get_mails(missing_idents, include_body=True)))
        except Exception, e:  # this is a event handler, don't let exceptions escape
            logger.error(e)

    def __eq__(self, other):
        return other and other.mailbox_name == self.mailbox_name

    def __hash__(self):
        return self.mailbox_name.__hash__()

    def __repr__(self):
        return 'MailboxListener: ' + self.mailbox_name


@defer.inlineCallbacks
def listen_all_mailboxes(account, search_engine, mail_store):
    mailboxes = yield account.list_all_mailbox_names()
    for mailbox_name in mailboxes:
        yield MailboxIndexerListener.listen(account, mailbox_name, mail_store, search_engine)
