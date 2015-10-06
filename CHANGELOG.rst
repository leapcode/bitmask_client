.. :changelog::

Changelog
---------

0.9.0rc4 October 05
+++++++++++++++++++

Features
~~~~~~~~
- `#7471 <https://leap.se/code/issues/7471>`_: Disable email firewall if we are running inside a docker container.

Bugfixes
~~~~~~~~
- `#7451 <https://leap.se/code/issues/7451>`_: Assign the timeout 'call later' before starting the sync to prevent race conditions.
- `#7503 <https://leap.se/code/issues/7503>`_: Handle soledad init fail after several retries.
- Remove bubble argument from the logbook NullHandler


0.9.0rc3 September 22
+++++++++++++++++++++

Features
~~~~~~~~
- `#4284 <https://leap.se/code/issues/4284>`_: Download specific smtp certificate from provider, instead of using the vpn one.
- `#7414 <https://leap.se/code/issues/7414>`_: Remove taskthread dependency, replace with custom (and small) code.
- `#7419 <https://leap.se/code/issues/7419>`_: Load credentials from environment variables and trigger login.


Bugfixes
~~~~~~~~
- `#7415 <https://leap.se/code/issues/7415>`_: Fix wrong argument number on window raise event.
- `#7448 <https://leap.se/code/issues/7448>`_: Fix hangs during logout.
- `#7453 <https://leap.se/code/issues/7453>`_: After a complete sync show the user the amount of unread emails.
- `#7470 <https://leap.se/code/issues/7470>`_: Fix bug with password change.
- `#7474 <https://leap.se/code/issues/7474>`_: Track soledad ready state on a shared place for easy access. Enable password change window.
- Authenticate properly logout calls to API.


0.9.0rc2 August 27
++++++++++++++++++

Features
~~~~~~~~
- `#7250 <https://leap.se/code/issues/7250>`_: Enable '--danger' for stable versions.
- `#7291 <https://leap.se/code/issues/7291>`_: Move the updater code from the launcher to the client.
- `#7342 <https://leap.se/code/issues/7342>`_: Added apply_updates.py script for the pyinstaller bundle.
- `#7353 <https://leap.se/code/issues/7353>`_: Add notifications of soledad sync progress to UI.
- `#7356 <https://leap.se/code/issues/7356>`_: Allow to disable EIP component on build.

Bugfixes
~~~~~~~~
- `#6594 <https://leap.se/code/issues/6594>`_: Handle disabled registration on provider.
- `#7149 <https://leap.se/code/issues/7149>`_: Start the events server when reactor is running.
- `#7273 <https://leap.se/code/issues/7273>`_: Logbook subscriber stop fails if not started.
- `#7273 <https://leap.se/code/issues/7273>`_: ZMQError: address already in use - logbook subscriber already started.
- `#7281 <https://leap.se/code/issues/7281>`_: Support a provider not providing location for the eip gateways.
- `#7319 <https://leap.se/code/issues/7319>`_: Raise the maxfiles limit in OSX
- `#7343 <https://leap.se/code/issues/7343>`_: Clean up and fix the tests.



0.9.0rc1 July 10
++++++++++++++++

Features
~~~~~~~~
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
- Add support to the new async-api of soledad

Bugfixes
~~~~~~~~
- `#6418 <https://leap.se/code/issues/6418>`_: Cannot change preseeded providers if checks for one fail.
- `#6424 <https://leap.se/code/issues/6424>`_: Do not disable autostart if the quit is triggered by a system logout.
- `#6541 <https://leap.se/code/issues/6541>`_: Client must honor the ports specified in eip-service.json.
- `#6654 <https://leap.se/code/issues/6654>`_: Regression fix, login attempt is made against previously selected provider.
- `#6682 <https://leap.se/code/issues/6682>`_: Handle user cancel keyring open operation, this prevents a bitmask freeze.
- `#6894 <https://leap.se/code/issues/6894>`_: Change 'ip' command location to support Fedora/RHEL distros.
- `#7093 <https://leap.se/code/issues/7093>`_: Fix controller attribute error.
- `#7126 <https://leap.se/code/issues/7126>`_: Don't run the event server on the backend for the standalone bundle since the launcher takes care of that.
- `#7185 <https://leap.se/code/issues/7185>`_: Log contains exported PGP Private Key.
- `#7222 <https://leap.se/code/issues/7222>`_: Run the zmq log subscriber in the background to avoid hitting the zmq's buffer limits.
- `#6536 <https://leap.se/code/issues/6536>`_, `#6568 <https://leap.se/code/issues/6568>`_, `#6691 <https://leap.se/code/issues/6691>`_: Refactor soledad sync to do it the twisted way.
- Fix the bootstrap script for developers so it works on Fedora/RHEL systems where there is /usr/lib64 for python libs.
- Fix soledad bootstrap sync retries.


0.8.1 February 25
+++++++++++++++++

Features
~~~~~~~~
- `#6646 <https://leap.se/code/issues/6658>`_: Gracefully fall back to ZMQ ipc sockets with restricted access if CurveZMQ is not available.
- `#6717 <https://leap.se/code/issues/6717>`_: Split changes log into changelog and history.

Bugfixes
~~~~~~~~
- `#6654 <https://leap.se/code/issues/6654>`_: Regression fix, login attempt is made against previously selected provider.
- `#6058 <https://leap.se/code/issues/6058>`_: Support 'nobody' (used on Arch) as well as 'nogroup' as group names.


0.8.0 January 04 -- "Charlie and the code refactory"
++++++++++++++++++++++++++++++++++++++++++++++++++++

Features
~~~~~~~~
- #5873: Allow frontend and backend to be run separately.
- Refactor login widgets/logic.
- Improved changelog :).

Bugfixes
~~~~~~~~
- #6058: Support 'nobody' (used on Arch) as well as 'nogroup' as group names.
- #6123: Forward the right environment data to subprocess call.
- #6150: Do not allow Bitmask to start if there is no polkit agent running.
- #6631: Fix failing tests.
- #6638: Fix set initialization to support python 2.6.
- #6652: Fix regression: polkit agent is not automatically launched.
- #6654: Login attempt is made against previously selected provider.
- Create zmq certificates if they don't exist.
- Disable '--offline' flag temporarily.
- Make pkg/tuf/release.py handle removals in the repo.
- Reduce the wait for running threads timeout on quit.


0.7.0 December 12 -- the "One window to rule them all, and in the darkness bind them." release:
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

- Select current provider on EIP preferences. Closes #5815.
- Handle logout correctly when we stop_services to launch the
  wizard. Related to #5815.
- Properly remove /tmp/bitmask.lock. Closes #5866.
- Hide EIP Start button and display correct warning on missing helpers
  files. Closes #5945.
- Save default provider if changed on the combo box. Closes #5995.
- Update the EIP status on provider change. Closes #5996.
- Update and get ready to start a provider on change. Closes #5997.
- Use python2 to run bitmask-root to work fine on systems with python3
  as default. Closes #6048.
- Use python2.7 in bitmask-root shebang since is the common name for
  python 2 in Ubuntu, Debian, Arch. Related to #6048.
- Remove dict comprenension in util, for 2.6 compat.
- Login shall not wait for eip to finish if eip is not able to
  start. Closes #5994
- Properly send the token for querying the EIP certificate. Fixes
  #6060.
- Code cleanup and logging improvements.
- Add email firewall blocking other users to access bitmask imap &
  smtp. Closes #6040
- Remove the Advanced Key Management since we don't support stable
  mail yet. Closes #6087.
- Single combined preferences window. Closes #4704, #4119, #5885.
- Fix soledad imports (#5989).
- Make pkg/tuf/release.py handle removals in the repo
- Remove instructions/references of mail from the client. Closes #6140.
- Add support for the internal LXDE polkit agent. Closes #6043.
- Allow the server to set a custom --fragment openvpn option (#5933)
- Add Calyx.net as pinned provider. Closes #6518.


For older entries look at the HISTORY.rst file.
