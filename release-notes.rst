0.9.0 October 28
++++++++++++++++

We were very pleased to announce Bitmask stable 0.9.0 :tada:.

Here is a report that details some of the work we did along the way. It's been
9 months since we released our latest stable version. Its been a long and
steady haul with multiple release candidates.

Using the latest Bitmask, Linux users will be able to use our encrypted email
service, now in beta state! A Mac release is imminent and a windows release is
underway.

Currently we have a test provider for mail @ https://mail.bitmask.net This
provider is already bundled with Bitmask for easy access on the wizard. Please
help us test this and file bug reports here:
https://leap.se/code/projects/report-issues

NOTE: beta means that we expect things not to break but we don't promise you
won't get any headaches or lose some email, so please be careful.

----

Some numbers on what we have been doing all this time:

- we have closed **472** issues,
- we have closed **379** pull requests,
- adding up all the components changes we got **830** new commits

----

Here you have a list of the most notable changes since our latest stable
release.

Index of changes:

* `Bitmask Client`_ (0.8.1 → 0.9.0)
* `Soledad`_ (0.6.3 → 0.7.4)
* `Keymanager`_ (0.3.8 → 0.4.3)
* `Common`_ (0.3.10 → 0.4.4)
* `Mail`_ (0.3.11 → 0.4.0)

Bitmask Client
==============

Features
~~~~~~~~
- `#4284 <https://leap.se/code/issues/4284>`_: Download specific smtp certificate from provider, instead of using the vpn one.
- `#5526 <https://leap.se/code/issues/5526>`_: Make "check" button selected by default.
- `#6359 <https://leap.se/code/issues/6359>`_: Adapt bitmask to the new events api on leap.common.
- `#6360 <https://leap.se/code/issues/6360>`_: Use txzmq in backend.
- `#6368 <https://leap.se/code/issues/6368>`_: Add support to the new async-api of keymanager.
- `#6683 <https://leap.se/code/issues/6683>`_: Add ability to generate sumo tarball.
- `#6713 <https://leap.se/code/issues/6713>`_: Add support for xfce-polkit agent.
- `#6876 <https://leap.se/code/issues/6876>`_: Update api port for pinned riseup.
- `#7139 <https://leap.se/code/issues/7139>`_: Use logbook zmq handler to centralize logging.
- `#7140 <https://leap.se/code/issues/7140>`_: Implement a thread-safe zmq handler for logbook.
- `#7141 <https://leap.se/code/issues/7141>`_: Add log handler to display colored logs on the terminal.
- `#7142 <https://leap.se/code/issues/7142>`_: Add log handler to store logs on bitmask.log.
- `#7143 <https://leap.se/code/issues/7143>`_: Adapt existing log filter/silencer to the new logbook handler.
- `#7144 <https://leap.se/code/issues/7144>`_: Replace logging handler with logbook handler bitmask-wide.
- `#7162 <https://leap.se/code/issues/7162>`_: Log LSB-release info if available.
- `#7180 <https://leap.se/code/issues/7180>`_: Add log rotation for bitmask.log.
- `#7184 <https://leap.se/code/issues/7184>`_: Forward twisted logs to logging and handle logging logs with logbook.
- `#7250 <https://leap.se/code/issues/7250>`_: Enable ``--danger`` for stable versions.
- `#7291 <https://leap.se/code/issues/7291>`_: Move the updater code from the launcher to the client.
- `#7342 <https://leap.se/code/issues/7342>`_: Added ``apply_updates.py`` script for the pyinstaller bundle.
- `#7353 <https://leap.se/code/issues/7353>`_: Add notifications of soledad sync progress to UI.
- `#7356 <https://leap.se/code/issues/7356>`_: Allow to disable EIP component on build.
- `#7414 <https://leap.se/code/issues/7414>`_: Remove taskthread dependency, replace with custom (and small) code.
- `#7419 <https://leap.se/code/issues/7419>`_: Load credentials from environment variables and trigger login.
- `#7471 <https://leap.se/code/issues/7471>`_: Disable email firewall if we are running inside a docker container.
- Add support to the new async-api of soledad

Bugfixes
~~~~~~~~
- `#6418 <https://leap.se/code/issues/6418>`_: Cannot change preseeded providers if checks for one fail.
- `#6424 <https://leap.se/code/issues/6424>`_: Do not disable autostart if the quit is triggered by a system logout.
- `#6536 <https://leap.se/code/issues/6536>`_, `#6568 <https://leap.se/code/issues/6568>`_, `#6691 <https://leap.se/code/issues/6691>`_: Refactor soledad sync to do it the twisted way.
- `#6541 <https://leap.se/code/issues/6541>`_: Client must honor the ports specified in ``eip-service.json``.
- `#6594 <https://leap.se/code/issues/6594>`_: Handle disabled registration on provider.
- `#6654 <https://leap.se/code/issues/6654>`_: Regression fix, login attempt is made against previously selected provider.
- `#6682 <https://leap.se/code/issues/6682>`_: Handle user cancel keyring open operation, this prevents a bitmask freeze.
- `#6894 <https://leap.se/code/issues/6894>`_: Change ``ip`` command location to support Fedora/RHEL distros.
- `#7093 <https://leap.se/code/issues/7093>`_: Fix controller attribute error.
- `#7126 <https://leap.se/code/issues/7126>`_: Don't run the event server on the backend for the standalone bundle since the launcher takes care of that.
- `#7149 <https://leap.se/code/issues/7149>`_: Start the events server when reactor is running.
- `#7185 <https://leap.se/code/issues/7185>`_: Log contains exported PGP Private Key.
- `#7222 <https://leap.se/code/issues/7222>`_: Run the zmq log subscriber in the background to avoid hitting the zmq's buffer limits.
- `#7273 <https://leap.se/code/issues/7273>`_: Logbook subscriber stop fails if not started.
- `#7273 <https://leap.se/code/issues/7273>`_: ZMQError: address already in use - logbook subscriber already started.
- `#7281 <https://leap.se/code/issues/7281>`_: Support a provider not providing location for the eip gateways.
- `#7319 <https://leap.se/code/issues/7319>`_: Raise the maxfiles limit in OSX
- `#7343 <https://leap.se/code/issues/7343>`_: Clean up and fix the tests.
- `#7415 <https://leap.se/code/issues/7415>`_: Fix wrong argument number on window raise event.
- `#7448 <https://leap.se/code/issues/7448>`_: Fix hangs during logout.
- `#7451 <https://leap.se/code/issues/7451>`_: Assign the timeout 'call later' before starting the sync to prevent race conditions.
- `#7453 <https://leap.se/code/issues/7453>`_: After a complete sync show the user the amount of unread emails.
- `#7470 <https://leap.se/code/issues/7470>`_: Fix bug with password change.
- `#7474 <https://leap.se/code/issues/7474>`_: Track soledad ready state on a shared place for easy access. Enable password change window.
- `#7503 <https://leap.se/code/issues/7503>`_: Handle soledad init fail after several retries.
- `#7512 <https://leap.se/code/issues/7512>`_: Pass on standalone flag to common.
- `#7512 <https://leap.se/code/issues/7512>`_: Store logs in the right place.
- `#7512 <https://leap.se/code/issues/7512>`_: Store zmq certs in the right path.
- Authenticate properly logout calls to API.
- Fix soledad bootstrap sync retries.
- Fix the bootstrap script for developers so it works on Fedora/RHEL systems where there is ``/usr/lib64`` for python libs.
- Remove bubble argument from the logbook NullHandler

----

Soledad
=======

soledad.client
~~~~~~~~~~~~~~

Features
--------
- `#7353 <https://leap.se/code/issues/7353>`_: Improve how we send information on ``SOLEDAD_SYNC_SEND_STATUS`` and in ``SOLEDAD_SYNC_RECEIVE_STATUS``.
- `#5895 <https://leap.se/code/issues/5895>`_: Store all incoming documents in the sync db.
- `#6359 <https://leap.se/code/issues/6359>`_: Adapt soledad to the new events api on leap.common.
- `#6400 <https://leap.se/code/issues/6400>`_: Include the IV in the encrypted document MAC.
- `#6996 <https://leap.se/code/issues/6996>`_: Expose post-sync hooks via plugin system.
- Add a pool of HTTP/HTTPS connections that is able to verify the server certificate against a given CA certificate.
- Use twisted.enterprise.adbapi for access to the sync database.
- Use twisted.web.client for client sync.

Bugfixes
--------

- `#5855 <https://leap.se/code/issues/5855>`_: Reset syncer connection when getting HTTP error during sync.
- `#5975 <https://leap.se/code/issues/5975>`_: Wait for last post request to finish before starting a new one.
- `#6437 <https://leap.se/code/issues/6437>`_: Use TLS v1 in soledad client.
- `#6625 <https://leap.se/code/issues/6625>`_: Retry on sqlcipher thread timeouts.
- `#6757 <https://leap.se/code/issues/6757>`_: Fix the order of insertion of documents when using workers for decrypting incoming documents during a sync.
- `#6892 <https://leap.se/code/issues/6892>`_: Fix the log message when a local secret is not found so it's less confusing.
- `#6980 <https://leap.se/code/issues/6980>`_: Remove MAC from secrets file.
- `#7088 <https://leap.se/code/issues/7088>`_: Fix sync encrypter pool close queue error.
- `#7302 <https://leap.se/code/issues/7302>`_: Increase http request timeout time to 90s.
- `#7386 <https://leap.se/code/issues/7386>`_: Fix hanging sync by properly waiting db initialization on sync decrypter pool.
- `#7503 <https://leap.se/code/issues/7503>`_: Do not signal sync completion if sync failed.
- `#7503 <https://leap.se/code/issues/7503>`_: Handle soledad init fail after several retries.
- Always initialize the sync db to allow for both asynchronous encryption and asynchronous decryption when syncing.
- Avoid double decryption of documents.
- Bugfix: move sync db and encpool creation to api.
- Bugfix: refactor code loss.
- Bugfix: set active secret before saving local file.
- Bugfix: wrong sqlcipher passphrase now raises correctly.
- Fallback to utf-8 if confidence on chardet guessing is too low.
- Fix logging and graceful failing when exceptions are raised during sync.
- Fix the order of the events emited for incoming documents.
- Handle ``DatabaseDoesNotExist`` during sync.
- Handle ``MissingDesignDocError`` after get_sync_info.
- Handle missing design doc at GET (``get_sync_info``). Soledad server can handle this during sync.

Misc (CI, tests, refactor, packaging)
-------------------------------------

- `#2945 <https://leap.se/code/issues/2945>`_: Do not depend on pysqlite2.
- `#6797 <https://leap.se/code/issues/6797>`_: Add dependency on Twisted.
- `#7338 <https://leap.se/code/issues/7338>`_: refactor ``SoledadCrypto`` to remove circular dependency with ``SoledadSecrets``.
- Add tests for enc/dec pool.
- Improve helper scripts and dependencies listing.
- Improve log messages when concurrently fetching documents from the server.
- Lots of code restyling to pass CI tests.
- Refactor asynchronous encryption/decryption code to its own file.
- Refactor decription pool and http target to use a deferred instead of a waiting loop.
- Refactor details of making an HTTP request body and headers out of the send/fetch logic. This also makes it easier to enable batching.
- Refactor enc/dec pool to standardize start/stop of the pools.
- Remove dependency on simplejson.
- Split ``http_target`` into 4 modules, separating those responsibilities.


soledad.server
~~~~~~~~~~~~~~

Features
--------

- `#6785 <https://leap.se/code/issues/6785>`_: Use monthly token databases.
- Lots of code restyling to pass CI tests.
- Lots of work done to get tests passing.
- Remove dependency on simplejson.

Bugfixes
--------

- `#6436 <https://leap.se/code/issues/6436>`_: Run daemon as user soledad.
- `#6437 <https://leap.se/code/issues/6437>`_: Avoid use of SSLv3.
- `#6557 <https://leap.se/code/issues/6557>`_: Fix server initscript location.
- `#6797 <https://leap.se/code/issues/6797>`_: Add dependency on Twisted.
- `#6833 <https://leap.se/code/issues/6833>`_: Remove unneeded parameters from ``CouchServerState`` initialization.
- Fix a bug where `BadRequest` could be raised after everything was persisted.
- Fix server daemon uid and gid by passing them to twistd on the initscript.


soledad.common
~~~~~~~~~~~~~~

Features
--------

- `#6359 <https://leap.se/code/issues/6359>`_: Adapt soledad to the new events api on leap.common.
- Lots of code restyling to pass CI tests.
- Lots of work done to get tests passing.
- Refactor `couch.py` to separate persistence from logic while saving uploaded documents. Also simplify logic while checking for conflicts.
- Remove dependency on simplejson.

Bugfixes
--------
- `#5896 <https://leap.se/code/issues/5896>`_: Include couch design docs source files in source distribution and only compile ``ddocs.py`` when building the package.
- `#6671 <https://leap.se/code/issues/6671>`_: Bail out if ``cdocs/`` dir does not exist.
- `#6833 <https://leap.se/code/issues/6833>`_: Remove unneeded parameters from ``CouchServerState`` initialization.

----

Keymanager
==========

Features
~~~~~~~~

- `#5359 <https://leap.se/code/issues/5359>`_: Adapt to new events api on leap.common.
- `#5932 <https://leap.se/code/issues/5932>`_: Add ``fetch_key`` method to fetch keys from a URI.
- `#6211 <https://leap.se/code/issues/6211>`_: Upgrade keys if not successfully used and strict high validation level.
- `#6212 <https://leap.se/code/issues/6212>`_: Multi uid support.
- `#6240 <https://leap.se/code/issues/6240>`_: Upgrade key when signed by old key.
- `#6262 <https://leap.se/code/issues/6262>`_: Keep old key after upgrade.
- `#6299 <https://leap.se/code/issues/6299>`_: New soledad doc struct for encryption-keys.
- `#6346 <https://leap.se/code/issues/6346>`_: Use addresses instead of keys for encrypt, decrypt, sign & verify.
- `#6366 <https://leap.se/code/issues/6366>`_: Expose info about the signing key.
- `#6368 <https://leap.se/code/issues/6368>`_: Port keymanager to the new soledad async API.
- `#6815 <https://leap.se/code/issues/6815>`_: Fetched keys from other domain than its provider are set as 'Weak Chain' validation level.
- `KeyManager.put_key` now accepts also ascii keys.

Bugfixes
~~~~~~~~

- `#6022 <https://leap.se/code/issues/6022>`_: Fix call to python-gnupg's ``verify_file()`` method.
- `#7188 <https://leap.se/code/issues/7188>`_: Remove the dependency on ``enum34``.
- `#7274 <https://leap.se/code/issues/7274>`_: use async events api.
- `#7410 <https://leap.se/code/issues/7410>`_: add logging to fetch_key.
- `#7410 <https://leap.se/code/issues/7410>`_: catch request exceptions on key fetching.
- `#7420 <https://leap.se/code/issues/7420>`_: don't repush a public key with different address.
- `#7498 <https://leap.se/code/issues/7498>`_: self-repair the keyring if keys get duplicated.
- Don't repush a public key with different addres
- More verbosity in ``get_key`` wrong address log.
- Return always ``KeyNotFound`` failure if fetch keys fails on an unknown error.
- Use ``ca_bundle`` when fetching keys by url.

Misc (CI, tests, refactor, packaging)
-------------------------------------

- Cleanup API.
- Packaging improvements.
- Style changes.
- Tests updates.


----

Common
======

Features
~~~~~~~~

- `#7188 <https://leap.se/code/issues/7188>`_: Modify ``leap.common.events`` to use ZMQ. Closes #6359.
- Add a ``HTTPClient`` the twisted way.
- Add close method for http agent.
- Allow passing callback to HTTP client.
- Bugfix: HTTP timeout was not being cleared on abort.
- Bugfix: do not add a port string to non-tcp addresses.
- Fix code style and tests.
- Make https client use Twisted SSL validation and adds a reuse by default behavior on connection pool


Bugfixes
~~~~~~~~

- `#6994 <https://leap.se/code/issues/6994>`_: Fix time comparison between local and UTC times that caused the VPN certificates not being correctly downloaded on time.
- `#7089 <https://leap.se/code/issues/7089>`_: Fix regexp to allow ipc protocol in zmq sockets.
- `#7130 <https://leap.se/code/issues/7130>`_: Remove extraneous data from events logs.
- `#7234 <https://leap.se/code/issues/7234>`_: Add http request timeout.
- `#7259 <https://leap.se/code/issues/7259>`_: Add a flag to disable events framework.
- `#7274 <https://leap.se/code/issues/7274>`_: Expose async methods for events.
- `#7512 <https://leap.se/code/issues/7512>`_: Consider standalone flag when saving events certificates.
- Fix wrong ca_cert path inside bundle.
- Workaround for deadlock problem in zmq auth.

----

Mail
====

Features
~~~~~~~~

- `#3879 <https://leap.se/code/issues/3879>`_: Parse OpenPGP header and import keys from it.
- `#4692 <https://leap.se/code/issues/4692>`_: Don't add any footer to the emails.
- `#5359 <https://leap.se/code/issues/5359>`_: Adapt to new events api on leap.common.
- `#5937 <https://leap.se/code/issues/5937>`_: Discover public keys via attachment.
- `#6357 <https://leap.se/code/issues/6357>`_: Create a ``OutgoingMail`` class that has the logic for encrypting, signing and sending messages. Factors that logic out of ``EncryptedMessage`` so it can be used by other clients.
- `#6361 <https://leap.se/code/issues/6361>`_: Refactor email fetching outside IMAP to its own independient ``IncomingMail`` class.
- `#6617 <https://leap.se/code/issues/6617>`_: Add public key as attachment.
- `#6742 <https://leap.se/code/issues/6742>`_: Add listener for each email added to inbox in IncomingMail.
- `#6996 <https://leap.se/code/issues/6996>`_: Ability to reindex local UIDs after a soledad sync.
- Add very basic support for message sequence numbers.
- Expose generic and protocol-agnostic public mail API.
- Lots of style fixes and tests updates.
- Make use of the twisted-based, async soledad API.
- Send a BYE command to all open connections, so that the MUA is notified when the server is shutted down.

Bugfixes
~~~~~~~~

- `#6601 <https://leap.se/code/issues/6601>`_: Port ``enum`` to ``enum34``.
- `#7169 <https://leap.se/code/issues/7169>`_: Update SMTP gateway docs.
- `#7244 <https://leap.se/code/issues/7244>`_: Fix nested multipart rendering.
- `#7430 <https://leap.se/code/issues/7430>`_: If the auth token has expired signal the GUI to request her to log in again.
- `#7471 <https://leap.se/code/issues/7471>`_: Disable local only tcp bind on docker containers to allow access to IMAP and SMTP.
- `#7480 <https://leap.se/code/issues/7480>`_: Don't extract openpgp header if valid attached key.
- Bugfix: Return the first cdoc if no body found
- Bugfix: fix keyerror when inserting msg on ``pending_inserts`` dict.
- Bugfix: fixed syntax error in ``models.py``.
