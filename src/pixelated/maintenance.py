
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

from os.path import isfile
from mailbox import Maildir, mbox, MaildirMessage
import random

from leap.mail.adaptors.soledad import MetaMsgDocWrapper
from twisted.internet import reactor, defer
from twisted.internet.threads import deferToThread
from pixelated.adapter.mailstore.maintenance import SoledadMaintenance
from pixelated.config.leap import initialize_leap_single_user
from pixelated.config import logger, arguments
import logging

from leap.mail.constants import MessageFlags
from pixelated.support.mail_generator import MailGenerator

REPAIR_COMMAND = 'repair'
INTEGRITY_CHECK_COMMAND = 'integrity-check'


log = logging.getLogger(__name__)


def initialize():
    args = arguments.parse_maintenance_args()

    logger.init(debug=args.debug)

    @defer.inlineCallbacks
    def _run():
        leap_session = yield initialize_leap_single_user(
            args.leap_provider_cert,
            args.leap_provider_cert_fingerprint,
            args.credentials_file,
            organization_mode=False,
            leap_home=args.leap_home,
            initial_sync=_do_initial_sync(args))

        execute_command(args, leap_session)

    reactor.callWhenRunning(_run)
    reactor.run()


def _do_initial_sync(args):
    return (not _is_repair_command(args)) and (not _is_integrity_check_command(args))


def _is_repair_command(args):
    return args.command == REPAIR_COMMAND


def _is_integrity_check_command(args):
    return args.command == INTEGRITY_CHECK_COMMAND


def execute_command(args, leap_session):

    def init_soledad():
        return leap_session

    def get_soledad_handle(leap_session):
        soledad = leap_session.soledad

        return leap_session, soledad

    @defer.inlineCallbacks
    def soledad_sync(args):
        leap_session, soledad = args

        log.warn('Before sync')

        yield soledad.sync()

        log.warn('after sync')

        defer.returnValue(args)

    tearDown = defer.Deferred()

    prepare = deferToThread(init_soledad)
    prepare.addCallback(get_soledad_handle)
    prepare.addCallback(soledad_sync)
    add_command_callback(args, prepare, tearDown)
    tearDown.addCallback(soledad_sync)
    tearDown.addCallback(shutdown)
    tearDown.addErrback(shutdown_on_error)


def add_command_callback(args, prepareDeferred, finalizeDeferred):
    if args.command == 'reset':
        prepareDeferred.addCallback(delete_all_mails)
        prepareDeferred.addCallback(flush_to_soledad, finalizeDeferred)
    elif args.command == 'load-mails':
        prepareDeferred.addCallback(load_mails, args.file)
        prepareDeferred.addCallback(flush_to_soledad, finalizeDeferred)
    elif args.command == 'markov-generate':
        prepareDeferred.addCallback(
            markov_generate, args.file, int(args.limit), args.seed)
        prepareDeferred.addCallback(flush_to_soledad, finalizeDeferred)
    elif args.command == 'dump-soledad':
        prepareDeferred.addCallback(dump_soledad)
        prepareDeferred.chainDeferred(finalizeDeferred)
    elif args.command == 'sync':
        # nothing to do here, sync is already part of the chain
        prepareDeferred.chainDeferred(finalizeDeferred)
    elif args.command == INTEGRITY_CHECK_COMMAND:
        prepareDeferred.addCallback(integrity_check)
        prepareDeferred.chainDeferred(finalizeDeferred)
    elif args.command == REPAIR_COMMAND:
        prepareDeferred.addCallback(repair)
        prepareDeferred.chainDeferred(finalizeDeferred)
    else:
        print 'Unsupported command: %s' % args.command
        prepareDeferred.chainDeferred(finalizeDeferred)

    return finalizeDeferred


@defer.inlineCallbacks
def delete_all_mails(args):
    leap_session, soledad = args
    generation, docs = yield soledad.get_all_docs()

    for doc in docs:
        if doc.content.get('type', None) in ['head', 'cnt', 'flags']:
            soledad.delete_doc(doc)

    defer.returnValue(args)


def is_keep_file(mail):
    return mail['subject'] is None


def _is_new_mail(mail):
    return _is_maildir_msg(mail) and mail.get_subdir() == 'new'


def _is_maildir_msg(mail):
    return isinstance(mail, MaildirMessage)


@defer.inlineCallbacks
def _add_mail(store, folder_name, mail, flags, tags):
    created_mail = yield store.add_mail(folder_name, mail.as_string())
    leap_mail = yield store.get_mail(created_mail.mail_id)
    leap_mail.tags |= set(tags)
    for flag in flags:
        leap_mail.flags.add(flag)

    yield store.update_mail(leap_mail)


@defer.inlineCallbacks
def add_mail_folder(store, mailbox, folder_name, deferreds):
    yield store.add_mailbox(folder_name)

    for mail in mailbox:
        if is_keep_file(mail):
            continue

        if _is_maildir_msg(mail):
            flags = {MessageFlags.RECENT_FLAG} if _is_new_mail(mail) else set()

            if 'S' in mail.get_flags():
                flags = flags.add(MessageFlags.SEEN_FLAG)
            if 'R' in mail.get_flags():
                flags = flags.add(MessageFlags.ANSWERED_FLAG)
        else:
            flags = {MessageFlags.RECENT_FLAG}

        tags = mail['X-Tags'].split() if mail['X-Tags'] else []

        deferreds.append(_add_mail(store, folder_name, mail, flags, tags))


@defer.inlineCallbacks
def load_mails(args, mail_paths):
    leap_session, soledad = args
    store = leap_session.mail_store

    yield _load_mails_as_is(mail_paths, store)

    defer.returnValue(args)


@defer.inlineCallbacks
def _load_mails_as_is(mail_paths, store):
    deferreds = []

    for path in mail_paths:
        if isfile(path):
            mbox_mails = mbox(path, factory=None)
            yield add_mail_folder(store, mbox_mails, 'INBOX', deferreds)
        else:
            maildir = Maildir(path, factory=None)
            yield add_mail_folder(store, maildir, 'INBOX', deferreds)
            for mail_folder_name in maildir.list_folders():
                mail_folder = maildir.get_folder(mail_folder_name)
                yield add_mail_folder(store, mail_folder, mail_folder_name, deferreds)

    yield defer.gatherResults(deferreds, consumeErrors=True)


@defer.inlineCallbacks
def markov_generate(args, mail_paths, limit, seed):
    leap_session, soledad = args
    store = leap_session.mail_store

    username = leap_session.user_auth.username
    server_name = leap_session.provider.server_name

    markov_mails = _generate_mails(
        limit, mail_paths, seed, server_name, username)
    deferreds = []
    yield add_mail_folder(store, markov_mails, 'INBOX', deferreds)
    yield defer.gatherResults(deferreds, consumeErrors=True)

    defer.returnValue(args)


def _generate_mails(limit, mail_paths, seed, server_name, username):
    mails = []
    for path in mail_paths:
        mbox_mails = mbox(path, factory=None)
        mails.extend(mbox_mails)
    gen = MailGenerator(username, server_name, mails,
                        random=random.Random(seed))
    markov_mails = [gen.generate_mail() for _ in range(limit)]
    return markov_mails


def flush_to_soledad(args, finalize):
    leap_session, soledad = args

    def after_sync(_):
        finalize.callback((leap_session, soledad))

    d = soledad.sync()
    d.addCallback(after_sync)

    return args


@defer.inlineCallbacks
def dump_soledad(args):
    leap_session, soledad = args

    generation, docs = yield soledad.get_all_docs()

    for doc in docs:
        print doc
        print '\n'

    defer.returnValue(args)


@defer.inlineCallbacks
def integrity_check(args):
    leap_session, soledad = args

    generation, docs = yield soledad.get_all_docs()

    known_docs = {}

    print 'Analysing %d docs\n' % len(docs)

    # learn about all docs
    for doc in docs:
        known_docs[doc.doc_id] = doc

    for doc in docs:
        if doc.doc_id.startswith('M-'):
            meta = MetaMsgDocWrapper(doc_id=doc.doc_id, **doc.content)

            # validate header doc
            if meta.hdoc not in known_docs:
                print 'Error: Could not find header doc %s for meta %s' % (meta.hdoc, doc.doc_id)

            if meta.fdoc not in known_docs:
                print 'Error: Could not find flags doc %s for meta %s' % (meta.fdoc, doc.doc_id)

            for cdoc in meta.cdocs:
                if cdoc not in known_docs:
                    print 'Error: Could not find content doc %s for meta %s' % (cdoc, meta.doc_id)

    defer.returnValue(args)


@defer.inlineCallbacks
def repair(args):
    leap_session, soledad = args

    yield SoledadMaintenance(soledad).repair()

    defer.returnValue(args)


def shutdown(args):
    # time.sleep(30)
    reactor.stop()


def shutdown_on_error(error):
    print error
    shutdown(None)

if __name__ == '__main__':
    initialize()
