# -*- coding: utf-8 -*-
# plumber.py
# Copyright (C) 2013, 2014  LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Utils for manipulating local mailboxes.
"""
import logging
import getpass
import os

from collections import defaultdict
from functools import partial

from twisted.internet import defer

from leap.bitmask.config.leapsettings import LeapSettings
from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.util import flatten, get_path_prefix
from leap.bitmask.services.soledad.soledadbootstrapper import get_db_paths

from leap.mail.imap.account import SoledadBackedAccount
from leap.soledad.client import Soledad

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def initialize_soledad(uuid, email, passwd,
                       secrets, localdb,
                       gnupg_home, tempdir):
    """
    Initializes soledad by hand

    :param email: ID for the user
    :param gnupg_home: path to home used by gnupg
    :param tempdir: path to temporal dir
    :rtype: Soledad instance
    """
    # XXX TODO unify with an authoritative source of mocks
    # for soledad (or partial initializations).
    # This is copied from the imap tests.

    server_url = "http://provider"
    cert_file = ""

    class Mock(object):
        def __init__(self, return_value=None):
            self._return = return_value

        def __call__(self, *args, **kwargs):
            return self._return

    class MockSharedDB(object):

        get_doc = Mock()
        put_doc = Mock()
        lock = Mock(return_value=('atoken', 300))
        unlock = Mock(return_value=True)

        def __call__(self):
            return self

    Soledad._shared_db = MockSharedDB()
    soledad = Soledad(
        uuid,
        passwd,
        secrets,
        localdb,
        server_url,
        cert_file)

    return soledad


class MBOXPlumber(object):
    """
    An class that can fix things inside a soledadbacked account.
    The idea is to gather in this helper different fixes for mailboxes
    that can be invoked when data migration in the client is needed.
    """

    def __init__(self, userid, passwd, mdir=None):
        """
        Initialize the plumber with all that's needed to authenticate
        against the provider.

        :param userid: user identifier, foo@bar
        :type userid: basestring
        :param passwd: the soledad passphrase
        :type passwd: basestring
        :param mdir: a path to a maildir to import
        :type mdir: str or None
        """
        self.userid = userid
        self.passwd = passwd
        user, provider = userid.split('@')
        self.user = user
        self.mdir = mdir
        self.sol = None
        self._settings = LeapSettings()

        provider_config_path = os.path.join(
            get_path_prefix(),
            "leap", "providers",
            provider, "provider.json")
        provider_config = ProviderConfig()
        loaded = provider_config.load(provider_config_path)
        if not loaded:
            print "could not load provider config!"
            return self.exit()

    def _init_local_soledad(self):
        """
        Initialize local Soledad instance.
        """
        self.uuid = self._settings.get_uuid(self.userid)
        if not self.uuid:
            print "Cannot get UUID from settings. Log in at least once."
            return self.exit()
        print "UUID: %s" % (self.uuid)

        secrets, localdb = get_db_paths(self.uuid)

        self.sol = initialize_soledad(
            self.uuid, self.userid, self.passwd,
            secrets, localdb, "/tmp", "/tmp")
        self.acct = SoledadBackedAccount(self.userid, self.sol)
    #
    # Account repairing
    #

    def repair_account(self, *args):
        """
        Repair mbox uids for all mboxes in this account.
        """
        self._init_local_soledad()
        for mbox_name in self.acct.mailboxes:
            self.repair_mbox_uids(mbox_name)
        print "done."
        self.exit()

    def repair_mbox_uids(self, mbox_name):
        """
        Repair indexes for a given mbox.

        :param mbox_name: mailbox to repair
        :type mbox_name: basestring
        """
        print
        print "REPAIRING INDEXES FOR MAILBOX %s" % (mbox_name,)
        print "----------------------------------------------"
        mbox = self.acct.getMailbox(mbox_name)
        len_mbox = mbox.getMessageCount()
        print "There are %s messages" % (len_mbox,)

        last_ok = True if mbox.last_uid == len_mbox else False
        uids_iter = mbox.messages.all_msg_iter()
        dupes = self._has_dupes(uids_iter)
        if last_ok and not dupes:
            print "Mbox does not need repair."
            return

        # XXX CHANGE? ----
        msgs = mbox.messages.get_all()
        for zindex, doc in enumerate(msgs):
            mindex = zindex + 1
            old_uid = doc.content['uid']
            doc.content['uid'] = mindex
            self.sol.put_doc(doc)
            if mindex != old_uid:
                print "%s -> %s (%s)" % (mindex, doc.content['uid'], old_uid)

        old_last_uid = mbox.last_uid
        mbox.last_uid = len_mbox
        print "LAST UID: %s (%s)" % (mbox.last_uid, old_last_uid)

    def _has_dupes(self, sequence):
        """
        Return True if the given sequence of ints has duplicates.

        :param sequence: a sequence of ints
        :type sequence: sequence
        :rtype: bool
        """
        d = defaultdict(lambda: 0)
        for uid in sequence:
            d[uid] += 1
            if d[uid] != 1:
                return True
        return False

    #
    # Maildir import
    #
    def import_mail(self, mail_filename):
        """
        Import a single mail into a mailbox.

        :param mbox: the Mailbox instance to save in.
        :type mbox: SoledadMailbox
        :param mail_filename: the filename to the mail file to save
        :type mail_filename: basestring
        :return: a deferred
        """
        def saved(_):
            print "message added"

        with open(mail_filename) as f:
            mail_string = f.read()
            uid = self._mbox.getUIDNext()
            print "saving with UID: %s" % uid
            d = self._mbox.messages.add_msg(mail_string, uid=uid)
        return d

    def import_maildir(self, mbox_name="INBOX"):
        """
        Import all mails in a maildir.

        We will process all subfolders as beloging
        to the same mailbox (cur, new, tmp).
        """
        # TODO parse hierarchical subfolders into
        # inferior mailboxes.

        if not os.path.isdir(self.mdir):
            print "ERROR: maildir path does not exist."
            return

        self._init_local_soledad()
        mbox = self.acct.getMailbox(mbox_name)
        self._mbox = mbox
        len_mbox = mbox.getMessageCount()

        mail_files_g = flatten(
            map(partial(os.path.join, f), files)
            for f, _, files in os.walk(self.mdir))

        # we only coerce the generator to give the
        # len, but we could skip than and inform at the end.
        mail_files = list(mail_files_g)
        print "Got %s mails to import into %s (%s)" % (
            len(mail_files), mbox_name, len_mbox)

        def all_saved(_):
            print "all messages imported"

        deferreds = []
        for f_name in mail_files:
            deferreds.append(self.import_mail(f_name))
        d1 = defer.gatherResults(deferreds, consumeErrors=False)
        d1.addCallback(all_saved)
        d1.addCallback(self._cbExit)

    def _cbExit(self, ignored):
        return self.exit()

    def exit(self):
        from twisted.internet import reactor
        if self.sol:
            self.sol.close()
        try:
            reactor.stop()
        except Exception:
            pass
        return


def repair_account(userid):
    """
    Start repair process for a given account.

    :param userid: the user id (email-like)
    """
    from twisted.internet import reactor
    passwd = unicode(getpass.getpass("Passphrase: "))

    # go mario!
    plumber = MBOXPlumber(userid, passwd)
    reactor.callLater(1, plumber.repair_account)
    reactor.run()


def import_maildir(userid, maildir_path):
    """
    Start import-maildir process for a given account.

    :param userid: the user id (email-like)
    """
    from twisted.internet import reactor
    passwd = unicode(getpass.getpass("Passphrase: "))

    # go mario!
    plumber = MBOXPlumber(userid, passwd, mdir=maildir_path)
    reactor.callLater(1, plumber.import_maildir)
    reactor.run()


if __name__ == "__main__":
    import sys

    logging.basicConfig()

    if len(sys.argv) != 3:
        print "Usage: plumber [repair|import] <username>"
        sys.exit(1)

    # this would be better with a dict if it grows
    if sys.argv[1] == "repair":
        repair_account(sys.argv[2])
    if sys.argv[1] == "import":
        print "Not implemented yet."
