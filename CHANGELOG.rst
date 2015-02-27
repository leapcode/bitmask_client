.. :changelog::

Changelog
---------

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
